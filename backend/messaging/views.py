from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q
from .models import Conversation, ConversationParticipant, Message, EncryptedMessageContent
from users.models import CustomUser, UserKey, UserBlock
from .forms import MessageForm, CreateGroupForm
from friends.models import Notification
from django.conf import settings
from cryptography.fernet import Fernet
from users.models import UserBlock

@login_required
def conversation_list(request):
    # Get all conversations where the user is a participant
    participant_conversations = ConversationParticipant.objects.filter(user=request.user).select_related('conversation')
    
    conversations = []
    for participant in participant_conversations:
        conversation = participant.conversation

         # For direct conversations, get the other user
        other_user = None
        if conversation.conversation_type == 'direct':
            other_user = conversation.get_other_participant(request.user)
            
            # Skip conversations with blocked users
            if other_user and UserBlock.objects.filter(
                (Q(blocker=request.user) & Q(blocked_user=other_user)) |
                (Q(blocker=other_user) & Q(blocked_user=request.user))
            ).exists():
                continue
        
        # For group conversations, check if any participant is blocked
        elif conversation.conversation_type == 'group':
            other_participants = conversation.participants.exclude(user=request.user).values_list('user', flat=True)
            blocked_users = UserBlock.objects.filter(
                (Q(blocker=request.user) & Q(blocked_user__in=other_participants)) |
                (Q(blocker__in=other_participants) & Q(blocked_user=request.user))
            ).exists()
            
            if blocked_users:
                continue
        
        # Get the last message for this conversation
        last_message = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
        
        # For direct conversations, get the other user
        other_user = None
        if conversation.conversation_type == 'direct':
            other_user = conversation.get_other_participant(request.user)
        
        conversations.append({
            'conversation': conversation,
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': Message.objects.filter(
                conversation=conversation,
                is_read=False
            ).exclude(sender=request.user).count()
        })
    
    return render(request, 'messaging/conversation_list.html', {
        'conversations': conversations
    })

@login_required
def start_conversation(request, user_id):
    print(f"Start conversation called with user_id: {user_id}")
    other_user = get_object_or_404(CustomUser, id=user_id)

    # Check for blocks
    if UserBlock.objects.filter(
        (Q(blocker=request.user) & Q(blocked_user=other_user)) |
        (Q(blocker=other_user) & Q(blocked_user=request.user))
    ).exists():
        django_messages.error(request, "You cannot start a conversation with this user.")
        return redirect('conversation_list')
    
    # Check if a conversation already exists between these users
    participant_pairs = ConversationParticipant.objects.filter(user=request.user)
    
    existing_conversation = None
    for participant in participant_pairs:
        if participant.conversation.conversation_type == 'direct':
            # Check if the other user is also in this conversation
            if ConversationParticipant.objects.filter(
                conversation=participant.conversation,
                user=other_user
            ).exists():
                existing_conversation = participant.conversation
                break
    
    if existing_conversation:
        return redirect('view_conversation', conversation_id=existing_conversation.id)
    
    # Create a new conversation
    conversation = Conversation.objects.create(conversation_type='direct')
    
    # Add both users as participants
    ConversationParticipant.objects.create(conversation=conversation, user=request.user)
    ConversationParticipant.objects.create(conversation=conversation, user=other_user)
    
    return redirect('view_conversation', conversation_id=conversation.id)

@login_required
def view_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Check if the user is a participant
    participant = get_object_or_404(ConversationParticipant, conversation=conversation, user=request.user)
    
    # Get other participants
    participants = conversation.participants.exclude(user=request.user)
    
    # Check if any participant has blocked the user or if the user has blocked any participant
    for p in participants:
        if UserBlock.objects.filter(
            (Q(blocker=request.user) & Q(blocked_user=p.user)) |
            (Q(blocker=p.user) & Q(blocked_user=request.user))
        ).exists():
            django_messages.error(request, "You cannot view this conversation due to a user block.")
            return redirect('conversation_list')
    
    # Mark messages as read
    Message.objects.filter(
        conversation=conversation,
        is_read=False
    ).exclude(sender=request.user).update(is_read=True)
    
    # Get messages
    messages_qs = Message.objects.filter(conversation=conversation).order_by('created_at')
    
    # Get user's encryption private key from session (temporary for demo)
    encryption_private_key = request.session.get('encryption_private_key')
    
    # Check if user has active keys
    has_keys = UserKey.objects.filter(user=request.user, is_active=True).exists()
    
    # Decrypt messages and prepare for display
    messages_list = []
    key = settings.ENCRYPTION_KEY.encode()
    f = Fernet(key)
    
    for msg in messages_qs:
        message_data = {
            'id': msg.id,
            'sender': msg.sender,
            'created_at': msg.created_at,
            'is_mine': msg.sender == request.user,
            'is_media': msg.is_media_message,
            'media_type': msg.media_type,
            'media_url': msg.media_file.url if msg.media_file else None,
            'blockchain_verified': msg.integrity_verified
        }
        
        # Handle standard encrypted messages
        if not msg.is_encrypted and msg.encrypted_content:
            try:
                message_data['content'] = f.decrypt(msg.encrypted_content.encode()).decode()
            except Exception as e:
                message_data['content'] = "[Encrypted message]"
                
        # Handle E2E encrypted messages
        elif msg.is_encrypted:
            if encryption_private_key:
                try:
                    # Get the message content encrypted for this user
                    encrypted_content = msg.encrypted_contents.get(recipient=request.user)
                    
                    # Decrypt with user's private key
                    from messaging.utils import decrypt_message
                    decrypted_content = decrypt_message(
                        encryption_private_key,
                        encrypted_content.encrypted_content
                    )
                    
                    if decrypted_content:
                        message_data['content'] = decrypted_content
                    else:
                        message_data['content'] = "[Could not decrypt message]"
                except Exception as e:
                    message_data['content'] = "[End-to-end encrypted message - Error decrypting]"
            else:
                message_data['content'] = "[End-to-end encrypted message - No private key available]"
        else:
            message_data['content'] = ""
        
        # Check signature if present
        if msg.signature and not msg.is_mine:
            # Get sender's signing public key
            try:
                signing_key = UserKey.objects.get(user=msg.sender, key_type='signing', is_active=True)
                
                # Verify signature
                from messaging.utils import verify_signature
                is_verified = verify_signature(
                    signing_key.public_key,
                    message_data['content'],
                    msg.signature
                )
                
                message_data['signature_verified'] = is_verified
            except UserKey.DoesNotExist:
                message_data['signature_verified'] = False
        
        messages_list.append(message_data)
    
    # Handle message form
    form = MessageForm()
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            content = form.cleaned_data.get('content')
            media_file = form.cleaned_data.get('media_file')
            media_type = form.cleaned_data.get('media_type')
            
            # Verify the user is verified for media sharing
            if media_file and not request.user.is_verified:
                django_messages.warning(request, "You need to verify your account to send media.")
                return redirect('verification_request')
            
            # Get signing private key
            signing_private_key = request.session.get('signing_private_key')
            
            # Create message
            message = Message(
                conversation=conversation,
                sender=request.user,
                media_type=media_type if media_file else 'none',
                is_encrypted=form.cleaned_data.get('enable_e2e', False)
            )
            
            # For media messages, we don't use E2E encryption
            if media_file:
                message.is_encrypted = False
                
            # Add content if provided
            if content:
                # For E2E encryption
                if message.is_encrypted:
                    # Create the message without standard encryption
                    message.save()
                    
                    # Encrypt with each recipient's public key
                    for participant in participants:
                        try:
                            # Get recipient's encryption public key
                            encryption_key = UserKey.objects.get(
                                user=participant.user, 
                                key_type='encryption',
                                is_active=True
                            )
                            
                            # Sign content if private key available
                            signed_content = content
                            if signing_private_key:
                                from messaging.utils import sign_message
                                signature = sign_message(signing_private_key, content)
                                if signature:
                                    message.signature = signature
                            
                            # Encrypt content for this recipient
                            from messaging.utils import encrypt_for_recipient
                            encrypted = encrypt_for_recipient(encryption_key.public_key, content)
                            
                            if encrypted:
                                # Store encrypted content for this recipient
                                EncryptedMessageContent.objects.create(
                                    message=message,
                                    recipient=participant.user,
                                    encrypted_content=encrypted
                                )
                        except UserKey.DoesNotExist:
                            # Skip recipients without encryption keys
                            pass
                    
                    # Also encrypt for the sender (so they can see their own messages)
                    try:
                        sender_key = UserKey.objects.get(
                            user=request.user, 
                            key_type='encryption',
                            is_active=True
                        )
                        
                        from messaging.utils import encrypt_for_recipient
                        encrypted = encrypt_for_recipient(sender_key.public_key, content)
                        
                        if encrypted:
                            EncryptedMessageContent.objects.create(
                                message=message,
                                recipient=request.user,
                                encrypted_content=encrypted
                            )
                    except UserKey.DoesNotExist:
                        pass
                        
                else:
                    # Standard encryption
                    message.encrypt_message(content)
                    
                    # Sign with private key if available
                    if signing_private_key:
                        from messaging.utils import sign_message
                        signature = sign_message(signing_private_key, content)
                        if signature:
                            message.signature = signature
            
            # Add media if provided
            if media_file:
                message.media_file = media_file
            
            message.save()
            
            # Create notifications for other participants
            for participant in participants:
                notification_content = "New message from {0}".format(request.user.username)
                if message.is_media_message:
                    notification_content = "{0} sent a {1}".format(
                        request.user.username, 
                        "photo" if message.is_image else "video"
                    )
                
                Notification.objects.create(
                    user=participant.user,
                    notification_type='message',
                    content=notification_content,
                    related_user=request.user
                )
            
            return redirect('view_conversation', conversation_id=conversation.id)

    if request.user.is_staff and request.GET.get('verify_integrity') == '1':
        from .blockchain import validate_conversation_integrity
        integrity_results = validate_conversation_integrity(conversation_id)
        
        # Display results
        if integrity_results["unverified_count"] > 0:
            django_messages.warning(request, f"Blockchain integrity check: {integrity_results['unverified_count']} message(s) failed verification!")
        elif integrity_results["missing_from_blockchain"] > 0:
            django_messages.info(request, f"Blockchain integrity check: {integrity_results['missing_from_blockchain']} message(s) not in blockchain.")
        else:
            django_messages.success(request, f"Blockchain integrity check passed for all {integrity_results['verified_count']} messages!")
        
    is_staff = request.user.is_staff
    
    return render(request, 'messaging/view_conversation.html', {
        'conversation': conversation,
        'participants': participants,
        'messages_list': messages_list,
        'form': form,
        'is_group': conversation.is_group,
        'is_admin': participant.is_admin,
        'is_verified': request.user.is_verified,
        'has_keys': has_keys,
        'has_private_keys': bool(encryption_private_key),
        'is_staff': is_staff
    })

@login_required
def create_group(request):
    # Only verified users can create groups
    if not request.user.is_verified:
        django_messages.error(request, "You need to be verified to create group conversations.")
        return redirect('verification_request')
    
    form = CreateGroupForm(user=request.user)
    
    if request.method == 'POST':
        form = CreateGroupForm(request.POST, user=request.user)
        if form.is_valid():
            conversation = form.save(commit=False)
            conversation.conversation_type = 'group'
            conversation.save()
            
            # Add creator as admin
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=request.user,
                is_admin=True
            )
            
            # Add other participants
            for user in form.cleaned_data['participants']:
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user=user
                )
                
                # Notify participants
                Notification.objects.create(
                    user=user,
                    notification_type='group_invite',
                    content=f"{request.user.username} added you to the group '{conversation.name}'",
                    related_user=request.user
                )
            
            django_messages.success(request, f"Group '{conversation.name}' created successfully.")
            return redirect('view_conversation', conversation_id=conversation.id)
    
    return render(request, 'messaging/create_group.html', {'form': form})

@login_required
def remove_from_group(request, conversation_id, user_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, conversation_type='group')
    
    # Check if the requester is an admin
    requester_participant = get_object_or_404(
        ConversationParticipant, 
        conversation=conversation,
        user=request.user,
        is_admin=True
    )
    
    # Get the participant to remove
    participant = get_object_or_404(
        ConversationParticipant,
        conversation=conversation,
        user_id=user_id
    )
    
    # Don't allow removing yourself
    if participant.user == request.user:
        django_messages.error(request, "You cannot remove yourself from the group. Leave the group instead.")
        return redirect('view_conversation', conversation_id=conversation.id)
    
    # Remove the participant
    user_name = participant.user.username
    participant.delete()
    
    django_messages.success(request, f"{user_name} has been removed from the group.")
    return redirect('view_conversation', conversation_id=conversation.id)

@login_required
def leave_group(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, conversation_type='group')
    
    # Get the participant
    participant = get_object_or_404(
        ConversationParticipant,
        conversation=conversation,
        user=request.user
    )
    
    # Check if this is the last admin
    is_last_admin = participant.is_admin and not ConversationParticipant.objects.filter(
        conversation=conversation,
        is_admin=True
    ).exclude(user=request.user).exists()
    
    if is_last_admin:
        # Find other participants
        other_participants = ConversationParticipant.objects.filter(
            conversation=conversation
        ).exclude(user=request.user)
        
        if other_participants.exists():
            # Make someone else admin
            new_admin = other_participants.first()
            new_admin.is_admin = True
            new_admin.save()
            
            # Notify the new admin
            Notification.objects.create(
                user=new_admin.user,
                notification_type='group_invite',
                content=f"You are now an admin of the group '{conversation.name}'",
                related_user=request.user
            )
    
    # Remove the participant
    participant.delete()
    
    django_messages.success(request, f"You have left the group '{conversation.name}'.")
    return redirect('conversation_list')

@login_required
def delete_group(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, conversation_type='group')
    
    # Check if the requester is an admin
    requester_participant = get_object_or_404(
        ConversationParticipant, 
        conversation=conversation,
        user=request.user,
        is_admin=True
    )
    
    # Get all participants to notify them
    participants = ConversationParticipant.objects.filter(
        conversation=conversation
    ).exclude(user=request.user)
    
    # Notify all participants
    for participant in participants:
        Notification.objects.create(
            user=participant.user,
            notification_type='group_invite',
            content=f"The group '{conversation.name}' has been deleted by {request.user.username}",
            related_user=request.user
        )
    
    # Delete the conversation (this will cascade delete all messages and participants)
    conversation_name = conversation.name
    conversation.delete()
    
    django_messages.success(request, f"Group '{conversation_name}' has been deleted.")
    return redirect('conversation_list')

@login_required
def view_media(request, message_id):
    # Get the message
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user is participant in conversation
    participant = get_object_or_404(
        ConversationParticipant,
        conversation=message.conversation,
        user=request.user
    )
    
    # Make sure it's a media message
    if not message.is_media_message:
        django_messages.error(request, "This message does not contain media.")
        return redirect('view_conversation', conversation_id=message.conversation.id)
    
    return render(request, 'messaging/view_media.html', {
        'message': message,
        'conversation': message.conversation
    })

@login_required
def manage_group_members(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, conversation_type='group')
    
    # Check if the requester is an admin
    requester_participant = get_object_or_404(
        ConversationParticipant, 
        conversation=conversation,
        user=request.user,
        is_admin=True
    )
    
    # Get all current participants
    current_participants = ConversationParticipant.objects.filter(
        conversation=conversation
    ).select_related('user')
    
    # Handle member addition
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_members':
            # Get friend IDs from form
            friend_ids = request.POST.getlist('friends')
            if friend_ids:
                # Get friend users
                from friends.models import FriendRequest
                from django.db.models import Q
                
                # Get user's verified friends
                friends_1 = FriendRequest.objects.filter(
                    sender=request.user,
                    status='accepted'
                ).values_list('receiver', flat=True)
                
                friends_2 = FriendRequest.objects.filter(
                    receiver=request.user,
                    status='accepted'
                ).values_list('sender', flat=True)
                
                friends = CustomUser.objects.filter(
                    Q(id__in=friends_1) | Q(id__in=friends_2),
                    id__in=friend_ids,
                    is_verified=True
                )
                
                # Get current participant user IDs
                current_participant_ids = current_participants.values_list('user__id', flat=True)
                
                # Add new members
                added_count = 0
                for friend in friends:
                    # Skip if already in group
                    if friend.id in current_participant_ids:
                        continue
                        
                    # Add to group
                    ConversationParticipant.objects.create(
                        conversation=conversation,
                        user=friend
                    )
                    
                    # Notify the user
                    Notification.objects.create(
                        user=friend,
                        notification_type='group_invite',
                        content=f"{request.user.username} added you to the group '{conversation.name}'",
                        related_user=request.user
                    )
                    
                    added_count += 1
                
                if added_count > 0:
                    django_messages.success(request, f"Added {added_count} new members to the group.")
                else:
                    django_messages.info(request, "No new members were added to the group.")
                
                return redirect('manage_group_members', conversation_id=conversation.id)
        
        elif action == 'make_admin':
            user_id = request.POST.get('user_id')
            if user_id:
                participant = get_object_or_404(
                    ConversationParticipant,
                    conversation=conversation,
                    user_id=user_id
                )
                participant.is_admin = True
                participant.save()
                
                # Notify the user
                Notification.objects.create(
                    user=participant.user,
                    notification_type='group_invite',
                    content=f"You are now an admin of the group '{conversation.name}'",
                    related_user=request.user
                )
                
                django_messages.success(request, f"{participant.user.username} is now an admin of this group.")
                return redirect('manage_group_members', conversation_id=conversation.id)
    
    # Get potential friends to add (friends who aren't already in the group)
    from friends.models import FriendRequest
    from django.db.models import Q
    
    # Get current participant user IDs
    current_participant_ids = current_participants.values_list('user__id', flat=True)
    
    # Get user's verified friends
    friends_1 = FriendRequest.objects.filter(
        sender=request.user,
        status='accepted'
    ).values_list('receiver', flat=True)
    
    friends_2 = FriendRequest.objects.filter(
        receiver=request.user,
        status='accepted'
    ).values_list('sender', flat=True)
    
    available_friends = CustomUser.objects.filter(
        Q(id__in=friends_1) | Q(id__in=friends_2),
        is_verified=True
    ).exclude(id__in=current_participant_ids)
    
    context = {
        'conversation': conversation,
        'participants': current_participants,
        'available_friends': available_friends
    }
    
    return render(request, 'messaging/manage_group_members.html', context)