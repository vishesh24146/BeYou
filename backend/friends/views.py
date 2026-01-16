from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from users.models import CustomUser
from .models import FriendRequest, Notification
from .forms import UserSearchForm
from users.models import UserBlock

@login_required
def search_users(request):
    form = UserSearchForm(request.GET)
    users = []
    
    if form.is_valid():
        search_query = form.cleaned_data.get('search_query')
        if search_query:
            # Get users matching query but exclude blocked users
            blocked_by_me = UserBlock.objects.filter(blocker=request.user).values_list('blocked_user', flat=True)
            blocking_me = UserBlock.objects.filter(blocked_user=request.user).values_list('blocker', flat=True)
            users = CustomUser.objects.filter(
                Q(username__icontains=search_query) | 
                Q(email__icontains=search_query)
            ).exclude(
                id=request.user.id
            ).exclude(
                id__in=blocked_by_me
            ).exclude(
                id__in=blocking_me
            )
    
    # Get the friendship status for each user
    user_statuses = {}
    for user in users:
        sent_request = FriendRequest.objects.filter(sender=request.user, receiver=user).first()
        received_request = FriendRequest.objects.filter(sender=user, receiver=request.user).first()
        
        if sent_request and sent_request.status == 'accepted':
            status = 'friend'
        elif sent_request and sent_request.status == 'pending':
            status = 'pending_sent'
        elif received_request and received_request.status == 'pending':
            status = 'pending_received'
        else:
            status = 'not_friend'
            
        user_statuses[user.id] = status
    
    return render(request, 'friends/search_users.html', {
        'form': form,
        'users': users,
        'user_statuses': user_statuses
    })

@login_required
def send_friend_request(request, user_id):
    receiver = get_object_or_404(CustomUser, id=user_id)

    if UserBlock.objects.filter(
        (Q(blocker=request.user) & Q(blocked_user=receiver)) |
        (Q(blocker=receiver) & Q(blocked_user=request.user))
    ).exists():
        messages.error(request, "You cannot send a friend request to this user.")
        return redirect('search_users')
    
    if receiver == request.user:
        messages.error(request, "You can't send a friend request to yourself.")
        return redirect('search_users')
    
    # Check if a request already exists
    if FriendRequest.objects.filter(sender=request.user, receiver=receiver).exists():
        messages.info(request, f"You already sent a friend request to {receiver.username}.")
        return redirect('search_users')
    
    if FriendRequest.objects.filter(sender=receiver, receiver=request.user).exists():
        messages.info(request, f"{receiver.username} already sent you a friend request. Check your notifications.")
        return redirect('search_users')
    
    # Create friend request
    friend_request = FriendRequest.objects.create(
        sender=request.user,
        receiver=receiver,
        status='pending'
    )
    
    # Create notification for the receiver
    Notification.objects.create(
        user=receiver,
        notification_type='friend_request',
        content=f"{request.user.username} sent you a friend request",
        related_user=request.user
    )
    
    messages.success(request, f"Friend request sent to {receiver.username}.")
    return redirect('search_users')

@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, receiver=request.user)
    
    if friend_request.status != 'pending':
        messages.error(request, "This friend request has already been processed.")
        return redirect('friend_requests')
    
    friend_request.status = 'accepted'
    friend_request.save()
    
    # Create notification for the sender
    Notification.objects.create(
        user=friend_request.sender,
        notification_type='friend_accept',
        content=f"{request.user.username} accepted your friend request",
        related_user=request.user
    )
    
    messages.success(request, f"You are now friends with {friend_request.sender.username}.")
    return redirect('notifications')

@login_required
def reject_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, receiver=request.user)
    
    if friend_request.status != 'pending':
        messages.error(request, "This friend request has already been processed.")
        return redirect('friend_requests')
    
    friend_request.status = 'rejected'
    friend_request.save()
    
    messages.success(request, f"You rejected the friend request from {friend_request.sender.username}.")
    return redirect('notifications')

@login_required
def friend_list(request):
    # Get users who have accepted friend requests with the current user
    friends_1 = FriendRequest.objects.filter(
        sender=request.user,
        status='accepted'
    ).values_list('receiver', flat=True)
    
    friends_2 = FriendRequest.objects.filter(
        receiver=request.user,
        status='accepted'
    ).values_list('sender', flat=True)
    
    friends = CustomUser.objects.filter(Q(id__in=friends_1) | Q(id__in=friends_2))
    
    return render(request, 'friends/friend_list.html', {'friends': friends})

@login_required
def notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Get friend requests from notifications
    friend_requests = FriendRequest.objects.filter(
        receiver=request.user,
        status='pending'
    )
    
    return render(request, 'friends/notifications.html', {
        'notifications': notifications,
        'friend_requests': friend_requests
    })

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    return redirect('notifications')