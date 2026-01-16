# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, VerificationForm, PasswordResetRequestForm, PasswordResetVerifyForm, SetNewPasswordForm, UserReportForm, MessageReportForm, ItemReportForm
from .models import UserBlock
from .models import CustomUser, PasswordResetRequest, Report, UserKey, LoginActivity
from django.utils import timezone
import pyotp
import qrcode
import base64
from io import BytesIO
from .forms import LoginWithCaptchaForm,RegisterWithCaptchaForm
from django.contrib import messages
from django.http import HttpResponse


@login_required
@user_passes_test(lambda u: u.is_staff)
def login_logs(request):
    """Admin view to see login activities"""
    
    # Get filter parameters
    username = request.GET.get('username', '')
    status = request.GET.get('status', '')
    ip_address = request.GET.get('ip_address', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    activities = LoginActivity.objects.all()
    
    # Apply filters
    if username:
        activities = activities.filter(username__icontains=username)
    
    if status:
        if status == 'success':
            activities = activities.filter(was_successful=True)
        elif status == 'failed':
            activities = activities.filter(was_successful=False)
    
    if ip_address:
        activities = activities.filter(ip_address__icontains=ip_address)
    
    if date_from:
        try:
            from datetime import datetime
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            activities = activities.filter(timestamp__gte=date_from)
        except:
            pass
    
    if date_to:
        try:
            from datetime import datetime, timedelta
            date_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)  # Include the end date
            activities = activities.filter(timestamp__lt=date_to)
        except:
            pass
    
    # Stats
    total_logins = activities.count()
    successful_logins = activities.filter(was_successful=True).count()
    failed_logins = activities.filter(was_successful=False).count()
    
    unique_users = activities.filter(was_successful=True).values('user').distinct().count()
    unique_ips = activities.values('ip_address').distinct().count()
    
    # Most recent failed attempts
    recent_failed = activities.filter(was_successful=False).order_by('-timestamp')[:10]
    
    # Get unique usernames with failed attempts
    usernames_with_failures = activities.filter(was_successful=False).values_list('username', flat=True).distinct()
    
    # Count failures by username
    failure_counts = {}
    for username in usernames_with_failures:
        if username:  # Skip None values
            count = activities.filter(username=username, was_successful=False).count()
            failure_counts[username] = count
    
    # Most failed attempts
    most_failed = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    context = {
        'activities': activities[:100],  # Limit to 100 for performance
        'total_count': total_logins,
        'successful_count': successful_logins,
        'failed_count': failed_logins,
        'unique_users': unique_users,
        'unique_ips': unique_ips,
        'recent_failed': recent_failed,
        'most_failed': most_failed,
        # Filter values for form
        'filter_username': username,
        'filter_status': status,
        'filter_ip_address': ip_address,
        'filter_date_from': date_from,
        'filter_date_to': date_to,
    }
    
    return render(request, 'users/login_logs.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def populate_blockchain(request):
    """Populate blockchain with existing messages"""
    from messaging.models import Message
    from messaging.blockchain import record_conversation_message
    
    # Get all messages without blockchain hashes
    message_objects = Message.objects.filter(blockchain_hash__isnull=True)  # Renamed to avoid conflict
    total = message_objects.count()
    
    # Process messages
    count = 0
    for message in message_objects:
        blockchain_hash = record_conversation_message(message)
        if blockchain_hash:
            # Update the message
            Message.objects.filter(pk=message.pk).update(
                blockchain_hash=blockchain_hash,
                integrity_verified=True
            )
            count += 1
    
    # Use Django's messages framework, not the message_objects variable
    messages.success(request, f"Added {count} messages to the blockchain out of {total} total.")
    
    # Get the next URL if provided
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    else:
        # Default redirect to blockchain explorer
        return redirect('blockchain_explorer')
    
@login_required
@user_passes_test(lambda u: u.is_staff)
def blockchain_explorer(request):
    """Admin view to explore the message blockchain"""
    from messaging.blockchain import get_blockchain_explorer_data, get_conversation_statistics
    from messaging.models import Conversation
    
    # Get blockchain data
    blockchain_data = get_blockchain_explorer_data()
    
    # Get conversation statistics
    conversation_stats = get_conversation_statistics()
    
    # Get conversation information
    conversations = {}
    for conv_id in conversation_stats.keys():
        try:
            from uuid import UUID
            conv = Conversation.objects.get(id=UUID(conv_id))
            if conv.conversation_type == 'direct':
                # Get participants
                participants = conv.participants.all()
                names = [p.user.username for p in participants]
                conversations[conv_id] = {
                    'id': conv_id,
                    'name': f"Direct: {' & '.join(names)}",
                    'type': 'direct'
                }
            else:
                conversations[conv_id] = {
                    'id': conv_id,
                    'name': conv.name,
                    'type': 'group'
                }
        except (Conversation.DoesNotExist, ValueError):
            conversations[conv_id] = {
                'id': conv_id,
                'name': f"Unknown Conversation ({conv_id})",
                'type': 'unknown'
            }
    
    # Print dictionary structure for debugging
    print(f"Conversations dictionary: {conversations}")
    print(f"Conversation stats: {conversation_stats}")
    
    # Get statistics
    total_blocks = len(blockchain_data)
    total_messages = sum(len(block['data'].get('messages', [])) for block in blockchain_data)
    
    context = {
        'blockchain_data': blockchain_data,
        'total_blocks': total_blocks,
        'total_messages': total_messages,
        'conversation_stats': conversation_stats,
        'conversations': conversations
    }
    
    return render(request, 'users/blockchain_explorer.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def conversation_blockchain(request, conversation_id):
    """View blockchain data for a specific conversation"""
    from messaging.blockchain import get_conversation_blockchain_data, validate_conversation_integrity
    from messaging.models import Conversation
    
    # Get conversation
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        messages.error(request, "Conversation not found")
        return redirect('blockchain_explorer')
    
    # Get blockchain data for this conversation
    blockchain_data = get_conversation_blockchain_data(conversation_id)
    
    # Validate conversation integrity
    integrity_results = validate_conversation_integrity(conversation_id)
    
    context = {
        'conversation': conversation,
        'blockchain_data': blockchain_data,
        'integrity_results': integrity_results,
        'total_blocks': len(blockchain_data)
    }
    
    return render(request, 'users/conversation_blockchain.html', context)

@login_required
def generate_keys(request):
    """Generate signing and encryption keys for the user"""
    from messaging.utils import generate_key_pair
    
    if request.method == 'POST':
        # Generate signing key pair
        signing_keys = generate_key_pair()
        UserKey.objects.create(
            user=request.user,
            public_key=signing_keys['public_key'],
            key_type='signing',
            is_active=True
        )
        
        # Generate encryption key pair
        encryption_keys = generate_key_pair()
        UserKey.objects.create(
            user=request.user,
            public_key=encryption_keys['public_key'],
            key_type='encryption',
            is_active=True
        )
        
        # In a real app, you'd send the private keys to the client securely
        # and never store them on the server
        # For this demo, we'll store them in the session temporarily
        request.session['signing_private_key'] = signing_keys['private_key']
        request.session['encryption_private_key'] = encryption_keys['private_key']
        
        messages.success(request, "Cryptographic keys generated successfully. Download your private keys for safekeeping.")
        return redirect('profile')
    
    return render(request, 'users/generate_keys.html')

@login_required
def download_private_keys(request):
    """Allow user to download their private keys"""
    signing_private_key = request.session.get('signing_private_key')
    encryption_private_key = request.session.get('encryption_private_key')
    
    if not signing_private_key or not encryption_private_key:
        messages.error(request, "No private keys found in your session. Please generate new keys.")
        return redirect('generate_keys')
    
    # Clear keys from session after viewing
    if request.method == 'POST':
        if 'signing_private_key' in request.session:
            del request.session['signing_private_key']
        if 'encryption_private_key' in request.session:
            del request.session['encryption_private_key']
        messages.success(request, "Private keys have been cleared from your session.")
        return redirect('profile')
    
    context = {
        'signing_private_key': signing_private_key,
        'encryption_private_key': encryption_private_key,
    }
    
    return render(request, 'users/download_private_keys.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_reports_list(request):
    """Admin view to list all reports"""
    # Get reports by status
    pending_reports = Report.objects.filter(status='pending').order_by('-created_at')
    investigating_reports = Report.objects.filter(status='investigating').order_by('-created_at')
    resolved_reports = Report.objects.filter(status__in=['resolved', 'dismissed']).order_by('-updated_at')[:50]  # Show last 50
    
    # Count by type
    user_reports_count = Report.objects.filter(report_type='user').count()
    message_reports_count = Report.objects.filter(report_type='message').count()
    item_reports_count = Report.objects.filter(report_type='item').count()
    
    return render(request, 'users/admin_reports_list.html', {
        'pending_reports': pending_reports,
        'investigating_reports': investigating_reports,
        'resolved_reports': resolved_reports,
        'user_reports_count': user_reports_count,
        'message_reports_count': message_reports_count,
        'item_reports_count': item_reports_count,
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_process_report(request, report_id):
    """Admin view to process a report"""
    report = get_object_or_404(Report, id=report_id)
    
    # Get the reported content based on report type
    reported_content = None
    if report.report_type == 'user':
        reported_content = report.reported_user
    elif report.report_type == 'message':
        from messaging.models import Message
        try:
            reported_content = Message.objects.get(id=report.reported_message)
        except Message.DoesNotExist:
            reported_content = "Message not found or deleted"
    elif report.report_type == 'item':
        from marketplace.models import Item
        try:
            reported_content = Item.objects.get(id=report.reported_item)
        except Item.DoesNotExist:
            reported_content = "Item not found or deleted"
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        report.admin_notes = admin_notes
        
        if action == 'investigate':
            report.status = 'investigating'
            report.save()
            messages.info(request, f"Report marked as under investigation.")
            
        elif action == 'dismiss':
            report.status = 'dismissed'
            report.action_taken = 'No action needed'
            report.save()
            messages.success(request, f"Report has been dismissed.")
            
        elif action == 'resolve':
            report.status = 'resolved'
            
            # Take specific actions based on resolution type
            resolution_type = request.POST.get('resolution_type')
            
            if resolution_type == 'warning':
                report.action_taken = f"Warning sent to {report.reported_user.username}"
                # Here you could implement sending a warning notification
                
            elif resolution_type == 'ban_temp':
                days = request.POST.get('ban_days', 7)
                report.action_taken = f"Temporary ban ({days} days) for {report.reported_user.username}"
                
                # Set user as inactive
                reported_user = report.reported_user
                reported_user.is_active = False
                reported_user.save()
                
                # You could store ban info in a new model for reactivation later
                
            elif resolution_type == 'ban_perm':
                report.action_taken = f"Permanent ban for {report.reported_user.username}"
                
                # Set user as inactive
                reported_user = report.reported_user
                reported_user.is_active = False
                reported_user.save()
                
            elif resolution_type == 'delete_content':
                report.action_taken = "Reported content deleted"
                
                # Delete the reported content based on type
                if report.report_type == 'message':
                    from messaging.models import Message
                    try:
                        message = Message.objects.get(id=report.reported_message)
                        message.delete()
                    except Message.DoesNotExist:
                        pass
                        
                elif report.report_type == 'item':
                    from marketplace.models import Item
                    try:
                        item = Item.objects.get(id=report.reported_item)
                        item.status = 'inactive'  # Or delete if preferred
                        item.save()
                    except Item.DoesNotExist:
                        pass
            
            report.save()
            messages.success(request, f"Report has been resolved.")
            
        return redirect('admin_reports_list')
    
    return render(request, 'users/admin_process_report.html', {
        'report': report,
        'reported_content': reported_content
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_user_management(request):
    """Admin view to manage users"""
    # Get users with reports against them
    users_with_reports = CustomUser.objects.filter(
        reports_against__isnull=False
    ).distinct()
    
    # Get banned users
    banned_users = CustomUser.objects.filter(is_active=False)
    
    # Get recent signups
    recent_users = CustomUser.objects.filter(
        date_joined__gte=timezone.now() - timezone.timedelta(days=7)
    ).order_by('-date_joined')
    
    return render(request, 'users/admin_user_management.html', {
        'users_with_reports': users_with_reports,
        'banned_users': banned_users,
        'recent_users': recent_users
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_ban_user(request, user_id):
    """Admin view to ban a user"""
    user_to_ban = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent banning staff or self
    if user_to_ban.is_staff or user_to_ban == request.user:
        messages.error(request, "You cannot ban staff members or yourself.")
        return redirect('admin_user_management')
    
    if request.method == 'POST':
        ban_type = request.POST.get('ban_type')
        reason = request.POST.get('reason', '')
        
        if ban_type == 'temp':
            days = int(request.POST.get('ban_days', 7))
            # Here you could implement a temp ban system with auto-reactivation
            # For now, just set as inactive
            user_to_ban.is_active = False
            user_to_ban.save()
            
            messages.success(request, f"{user_to_ban.username} has been temporarily banned for {days} days.")
            
        elif ban_type == 'perm':
            user_to_ban.is_active = False
            user_to_ban.save()
            
            messages.success(request, f"{user_to_ban.username} has been permanently banned.")
        
        return redirect('admin_user_management')
    
    return render(request, 'users/admin_ban_user.html', {'user_to_ban': user_to_ban})

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_unban_user(request, user_id):
    """Admin view to unban a user"""
    user_to_unban = get_object_or_404(CustomUser, id=user_id, is_active=False)
    
    if request.method == 'POST':
        user_to_unban.is_active = True
        user_to_unban.save()
        
        messages.success(request, f"{user_to_unban.username} has been unbanned and can now log in again.")
        return redirect('admin_user_management')
    
    return render(request, 'users/admin_unban_user.html', {'user_to_unban': user_to_unban})

@login_required
def report_user(request, user_id):
    reported_user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent self-reporting
    if reported_user == request.user:
        messages.error(request, "You cannot report yourself.")
        return redirect('profile')
    
    if request.method == 'POST':
        form = UserReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_user = reported_user
            report.report_type = 'user'
            report.save()
            
            messages.success(request, f"Your report against {reported_user.username} has been submitted and will be reviewed by our team.")
            return redirect('friend_list')
    else:
        form = UserReportForm()
    
    return render(request, 'users/report_user.html', {'form': form, 'reported_user': reported_user})

@login_required
def report_message(request, message_id):
    from messaging.models import Message
    
    # Validate message exists but don't need to load full content
    message = get_object_or_404(Message, id=message_id)
    conversation = message.conversation
    
    # Verify user is part of the conversation
    from messaging.models import ConversationParticipant
    participant = get_object_or_404(ConversationParticipant, conversation=conversation, user=request.user)
    
    if request.method == 'POST':
        form = MessageReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_user = message.sender
            report.reported_message = message.id
            report.report_type = 'message'
            report.save()
            
            messages.success(request, "Your report has been submitted and will be reviewed by our team.")
            return redirect('view_conversation', conversation_id=conversation.id)
    else:
        form = MessageReportForm()
    
    return render(request, 'users/report_message.html', {'form': form, 'message': message})

@login_required
def report_item(request, item_id):
    from marketplace.models import Item
    
    item = get_object_or_404(Item, id=item_id)
    
    if request.method == 'POST':
        form = ItemReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reported_user = item.seller
            report.reported_item = item.id
            report.report_type = 'item'
            report.save()
            
            messages.success(request, f"Your report for item '{item.name}' has been submitted and will be reviewed by our team.")
            return redirect('item_detail', item_id=item.id)
    else:
        form = ItemReportForm()
    
    return render(request, 'users/report_item.html', {'form': form, 'item': item})

@login_required
def block_user(request, user_id):
    user_to_block = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent self-blocking
    if user_to_block == request.user:
        messages.error(request, "You cannot block yourself.")
        return redirect('profile')
    
    # Check if already blocked
    if UserBlock.objects.filter(blocker=request.user, blocked_user=user_to_block).exists():
        messages.info(request, f"You have already blocked {user_to_block.username}.")
        return redirect('friend_list')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        # Check if they are friends before blocking
        from django.db.models import Q
        from friends.models import FriendRequest
        were_friends = FriendRequest.objects.filter(
            (Q(sender=request.user) & Q(receiver=user_to_block) & Q(status='accepted')) |
            (Q(sender=user_to_block) & Q(receiver=request.user) & Q(status='accepted'))
        ).exists()
        
        # Store this information in the session
        request.session[f'were_friends_{user_id}'] = were_friends
        
        # Create block record
        UserBlock.objects.create(
            blocker=request.user,
            blocked_user=user_to_block,
            reason=reason
        )
        
        # Remove any existing friend relationship
        FriendRequest.objects.filter(
            (Q(sender=request.user) & Q(receiver=user_to_block)) |
            (Q(sender=user_to_block) & Q(receiver=request.user))
        ).delete()
        
        messages.success(request, f"You have blocked {user_to_block.username}.")
        return redirect('blocked_users')
    
    return render(request, 'users/block_user.html', {'user_to_block': user_to_block})

@login_required
def unblock_user(request, user_id):
    user_to_unblock = get_object_or_404(CustomUser, id=user_id)
    block = get_object_or_404(UserBlock, blocker=request.user, blocked_user=user_to_unblock)
    
    # Check if they were friends before blocking (we'll need to store this information)
    were_friends = request.session.get(f'were_friends_{user_id}', False)
    
    if request.method == 'POST':
        # Delete the block record
        block.delete()
        
        # Check if the user wants to restore friendship
        restore_friendship = request.POST.get('restore_friendship') == 'yes'
        
        if restore_friendship:
            # Create a new accepted friend request
            from friends.models import FriendRequest
            FriendRequest.objects.create(
                sender=request.user,
                receiver=user_to_unblock,
                status='accepted'
            )
            messages.success(request, f"You have unblocked {user_to_unblock.username} and restored your friendship.")
        else:
            messages.success(request, f"You have unblocked {user_to_unblock.username}.")
        
        # Clear the session variable
        if f'were_friends_{user_id}' in request.session:
            del request.session[f'were_friends_{user_id}']
            
        return redirect('blocked_users')
    
    return render(request, 'users/unblock_user.html', {
        'user_to_unblock': user_to_unblock,
        'were_friends': were_friends
    })

@login_required
def blocked_users(request):
    blocks = UserBlock.objects.filter(blocker=request.user).select_related('blocked_user')
    return render(request, 'users/blocked_users.html', {'blocks': blocks})

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    
    if request.method == 'POST':
        form = RegisterWithCaptchaForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created for {user.username}! You are now logged in.')
            return redirect('download_keys')
    else:
        form = RegisterWithCaptchaForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request, username=None):
    """View for viewing own profile or other users' profiles"""
    if username:
        # Viewing someone else's profile
        user = get_object_or_404(CustomUser, username=username)
    else:
        # Viewing own profile
        user = request.user
    
    # Check if user is viewing someone else's profile
    is_own_profile = (user == request.user)
    signing_key = request.session.get('signing_private_key', '')
    encryption_key = request.session.get('encryption_private_key', '')
    
    has_keys = UserKey.objects.filter(user=request.user, is_active=True).count() >= 2
    
    # Check that keys exist and contain the expected content
    has_private_keys = (
        signing_key and 
        encryption_key and 
        '-----BEGIN PRIVATE KEY-----' in signing_key and 
        '-----BEGIN PRIVATE KEY-----' in encryption_key
    )
    
    # Check if this user is blocked
    is_blocked = False
    if not is_own_profile:
        is_blocked = UserBlock.objects.filter(blocker=request.user, blocked_user=user).exists()
    
    show_private_keys_message = has_keys and not has_private_keys

    if request.method == 'POST' and is_own_profile:
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        # Only initialize forms if viewing own profile
        if is_own_profile:
            u_form = UserUpdateForm(instance=request.user)
            p_form = ProfileUpdateForm(instance=request.user)
        else:
            u_form = None
            p_form = None
    
    context = {
        'user_profile': user,
        'is_own_profile': is_own_profile,
        'is_blocked': is_blocked,
        'has_keys': has_keys,
        'has_private_keys': has_private_keys,
        'show_private_keys_message': show_private_keys_message,
        'u_form': u_form,
        'p_form': p_form
    }
    
    return render(request, 'users/profile.html', context)





############################## UPDATING LOGIN ###########################################















# def login_view(request):
#     if request.user.is_authenticated:
#         return redirect('profile')
    
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
        
#         user = authenticate(request, username=username, password=password)
#         if user:
#             login(request, user)
#             messages.success(request, 'You have successfully logged in!')
#             return redirect('profile')  # This should redirect to your profile page
#         else:
#             messages.error(request, 'Invalid username or password.')
    
#     return render(request, 'users/login.html')







def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    form = LoginWithCaptchaForm(request.POST or None)
    
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, 'You have successfully logged in!')
                return redirect('profile')
            else:
                messages.error(request, 'Invalid username or password.')
    
    return render(request, 'users/login.html', {'form': form})











##########################################################################################################
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

@login_required
def verification_request(request):
    """View for users to submit verification requests"""
    user = request.user
    
    # Check if already verified
    if user.is_verified:
        messages.info(request, 'Your account is already verified.')
        return redirect('profile')
    
    # Check if verification is pending
    if user.verification_status == 'pending' and user.id_document:
        return render(request, 'users/verification_pending.html')
    
    if request.method == 'POST':
        form = VerificationForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.verification_status = 'pending'
            verification.verification_submitted_at = timezone.now()
            verification.save()
            
            messages.success(request, 'Your verification request has been submitted. You will be notified once approved.')
            return redirect('verification_pending')
    else:
        form = VerificationForm(instance=user)
    
    return render(request, 'users/verification_request.html', {'form': form})

@login_required
def verification_pending(request):
    """View for users with pending verification"""
    user = request.user
    
    if not user.id_document or not user.verification_status:
        return redirect('verification_request')
    
    if user.is_verified:
        messages.success(request, 'Your account is verified!')
        return redirect('profile')
    
    return render(request, 'users/verification_pending.html', {'user': user})

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_verification_list(request):
    """Admin view to list verification requests"""
    # Get pending verification requests - users who have submitted documents but aren't verified yet
    pending_requests = CustomUser.objects.filter(
        verification_status='pending',
        id_document__isnull=False,
        verification_reason__isnull=False
    ).order_by('verification_submitted_at')
    
    # Get processed requests - users who have been approved or rejected
    processed_requests = CustomUser.objects.filter(
        verification_status__in=['approved', 'rejected']
    ).order_by('-verification_processed_at')[:50]  # Show last 50
    
    # Get users who haven't submitted verification yet - no document or no reason
    not_submitted_users = CustomUser.objects.filter(
        Q(id_document__isnull=True) | 
        Q(verification_reason__isnull=True) |
        Q(verification_reason='')
    ).exclude(
        verification_status__in=['approved', 'rejected']
    ).exclude(is_staff=True).order_by('date_joined')
    
    return render(request, 'users/admin_verification_list.html', {
        'pending_requests': pending_requests,
        'processed_requests': processed_requests,
        'not_submitted_users': not_submitted_users
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def process_verification(request, user_id):
    """Admin view to approve/reject verification requests"""
    user_to_verify = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        user_to_verify.verification_notes = notes
        user_to_verify.verification_processed_at = timezone.now()
        
        if action == 'approve':
            user_to_verify.verification_status = 'approved'
            user_to_verify.is_verified = True
            messages.success(request, f"User {user_to_verify.username} has been verified.")
        elif action == 'reject':
            user_to_verify.verification_status = 'rejected'
            user_to_verify.is_verified = False
            messages.warning(request, f"Verification for {user_to_verify.username} has been rejected.")
        
        user_to_verify.save()
        return redirect('admin_verification_list')
    
    return render(request, 'users/process_verification.html', {
        'user_to_verify': user_to_verify
    })

@login_required
def premium_feature(request):
    if not request.user.is_verified:
        messages.warning(request, 'You must verify your account to access this feature.')
        return redirect('totp_setup')

    return render(request, 'users/premium_feature.html')

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('profile')
    return render(request, 'users/landing.html')

@login_required
def totp_setup(request):
    """View for setting up TOTP-based two-factor authentication"""
    user = request.user
    
    # Check if user already has TOTP set up
    if user.totp_secret:
        messages.info(request, 'Two-factor authentication is already enabled for your account.')
        return redirect('profile')
    
    # Generate a new TOTP secret if not in session
    if 'totp_secret' not in request.session:
        request.session['totp_secret'] = pyotp.random_base32()
    
    secret = request.session['totp_secret']
    
    # Create QR code
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(user.email, issuer_name="YourSocialApp")
    
    img = qrcode.make(uri)
    buffered = BytesIO()
    img.save(buffered)
    qr_code = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    if request.method == 'POST':
        # Verify the entered code
        verification_code = request.POST.get('verification_code')
        if totp.verify(verification_code):
            # Save the secret to the user's profile
            user.totp_secret = secret
            user.save()
            
            # Clear the session secret
            if 'totp_secret' in request.session:
                del request.session['totp_secret']
            
            messages.success(request, 'Two-factor authentication has been successfully enabled for your account.')
            return redirect('profile')
        else:
            messages.error(request, 'Invalid verification code. Please try again.')
    
    return render(request, 'users/totp_setup.html', {
        'qr_code': qr_code,
        'secret': secret,
        'user': user
    })

def password_reset_request(request):
    """Request a password reset - requires email address"""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                
                # Check if user has set up TOTP
                if not user.totp_secret:
                    messages.error(request, "You need to set up Two-Factor Authentication before you can reset your password.")
                    return redirect('login')
                
                # Create password reset request using the user's TOTP secret
                reset_request = PasswordResetRequest.objects.create(
                    user=user,
                    token=user.totp_secret,  # Use the existing TOTP secret
                    expires_at=timezone.now() + timezone.timedelta(minutes=10)
                )
                
                return redirect('password_reset_verify', reset_id=reset_request.id)
                
            except CustomUser.DoesNotExist:
                # Don't reveal if the email exists
                messages.warning(request, "If your email is registered and you have set up 2FA, you'll be redirected to the next step.")
                return redirect('login')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'users/password_reset_request.html', {'form': form})

def password_reset_verify(request, reset_id):
    """Verify the TOTP code from the authenticator app"""
    reset_request = get_object_or_404(PasswordResetRequest, id=reset_id)
    
    # Check if reset request is valid
    if not reset_request.is_valid():
        messages.error(request, "This password reset link has expired or has been used.")
        return redirect('password_reset_request')
    
    user = reset_request.user
    
    # Ensure the user has TOTP set up
    if not user.totp_secret:
        messages.error(request, "You must set up Two-Factor Authentication before you can reset your password.")
        return redirect('login')
    
    if request.method == 'POST':
        form = PasswordResetVerifyForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data['token']
            
            # Verify the token against the user's TOTP secret
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(token):
                # Token is valid, allow setting new password
                request.session['reset_user_id'] = reset_request.user.id
                request.session['reset_request_id'] = reset_request.id
                return redirect('password_reset_confirm')
            else:
                messages.error(request, "Invalid authenticator code. Please try again.")
    else:
        form = PasswordResetVerifyForm()
    
    return render(request, 'users/password_reset_verify.html', {
        'form': form,
        'user': user
    })

def password_reset_confirm(request):
    """Set a new password after successful TOTP verification"""
    # Check if we have a valid reset in session
    reset_user_id = request.session.get('reset_user_id')
    reset_request_id = request.session.get('reset_request_id')
    
    if not reset_user_id or not reset_request_id:
        messages.error(request, "Invalid password reset session.")
        return redirect('password_reset_request')
    
    try:
        user = CustomUser.objects.get(id=reset_user_id)
        reset_request = PasswordResetRequest.objects.get(id=reset_request_id, user=user)
        
        # Check if reset request is still valid
        if not reset_request.is_valid():
            messages.error(request, "This password reset session has expired.")
            return redirect('password_reset_request')
        
        if request.method == 'POST':
            form = SetNewPasswordForm(request.POST)
            if form.is_valid():
                # Set new password
                user.set_password(form.cleaned_data['password1'])
                user.save()
                
                # Mark reset request as used
                reset_request.is_used = True
                reset_request.save()
                
                # Clear session
                if 'reset_user_id' in request.session:
                    del request.session['reset_user_id']
                if 'reset_request_id' in request.session:
                    del request.session['reset_request_id']
                
                messages.success(request, "Your password has been changed successfully. You can now log in with your new password.")
                return redirect('login')
        else:
            form = SetNewPasswordForm()
        
        return render(request, 'users/password_reset_confirm.html', {'form': form})
    
    except (CustomUser.DoesNotExist, PasswordResetRequest.DoesNotExist):
        messages.error(request, "Invalid password reset session.")
        return redirect('password_reset_request')



############################################  
# In users/views.py
@login_required
def clear_session_keys(request):
    """Clear private keys from session"""
    if 'signing_private_key' in request.session:
        del request.session['signing_private_key']
    if 'encryption_private_key' in request.session:
        del request.session['encryption_private_key']
    return HttpResponse("Keys cleared")

# In users/views.py
@login_required
def reupload_keys(request):
    """Allow users to re-upload their private keys"""
    if request.method == 'POST':
        signing_key = request.POST.get('signing_key', '').strip()
        encryption_key = request.POST.get('encryption_key', '').strip()
        
        if signing_key and encryption_key:
            # Validate keys (simplified)
            if "BEGIN PRIVATE KEY" in signing_key and "BEGIN PRIVATE KEY" in encryption_key:
                request.session['signing_private_key'] = signing_key
                request.session['encryption_private_key'] = encryption_key
                messages.success(request, "Private keys uploaded successfully.")
                return redirect('profile')
            else:
                messages.error(request, "Invalid key format. Please ensure you're uploading the correct private keys.")
        else:
            messages.error(request, "Both keys are required.")
    
    return render(request, 'users/reupload_keys.html')




@login_required
def download_keys(request):
    """Allow users to download their private keys"""
    signing_private_key = request.session.get('signing_private_key')
    encryption_private_key = request.session.get('encryption_private_key')
    
    if not signing_private_key or not encryption_private_key:
        from django.core.cache import cache
        # Try to get from cache as a fallback
        cache_key = f"user_private_keys_{request.user.id}"
        cached_keys = cache.get(cache_key)
        
        if cached_keys:
            signing_private_key = cached_keys['signing_private_key']
            encryption_private_key = cached_keys['encryption_private_key']
            
            # Store in session
            request.session['signing_private_key'] = signing_private_key
            request.session['encryption_private_key'] = encryption_private_key
            
            # Delete from cache
            cache.delete(cache_key)
        else:
            messages.error(request, "Your private keys are not available. They may have expired or been cleared.")
            return redirect('profile')
    
    # Check if we need to clear the keys from session after view
    clear_after_view = request.GET.get('clear', 'false') == 'true'
    
    context = {
        'signing_private_key': signing_private_key,
        'encryption_private_key': encryption_private_key,
        'clear_after_view': clear_after_view
    }
    
    return render(request, 'users/download_keys.html', context)
