import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Pin, PinLike, PinComment, PinCheckin, Profile, Follow, Story, Notification, DirectMessage

# Helper: แปลงข้อมูลสถานที่ (Pin/Post) ให้อยู่ในรูปแบบ JSON ส่งให้ Frontend
def serialize_pin(pin, user=None):
    img_src = ''
    if pin.image:
        img_src = pin.image.url
    elif pin.image_url:
        img_src = pin.image_url
    
    likes_count = pin.likes.count()
    comments_list = [
        {
            'id': c.id,
            'name': c.author_name or (c.user.first_name or c.user.username if c.user else 'ผู้เยี่ยมชม'),
            'username': c.user.username if c.user else '',
            'avatar': (c.user.profile.avatar_url if hasattr(c.user, 'profile') else '') if c.user else '',
            'text': c.text,
            'emoji': c.emoji,
            'ts': c.created_at.isoformat()
        }
        for c in pin.comments.all().order_by('created_at')
    ]
    
    is_liked = False
    is_checked = False
    my_reaction = ''
    if user and user.is_authenticated:
        like_obj = pin.likes.filter(user=user).first()
        if like_obj:
            is_liked = True
            my_reaction = like_obj.reaction_emoji
        is_checked = pin.checkins.filter(user=user).exists()

    creator_name = pin.created_by.first_name or pin.created_by.username if pin.created_by else 'ผู้ใช้ TripGo'
    creator_avatar = ''
    if pin.created_by and hasattr(pin.created_by, 'profile'):
        creator_avatar = pin.created_by.profile.avatar_url

    return {
        'id': str(pin.id),
        'db_id': pin.id,
        'name': pin.name,
        'province': pin.province,
        'district': pin.district,
        'village': pin.village,
        'category': pin.category,
        'desc': pin.description,
        'latitude': pin.latitude,
        'longitude': pin.longitude,
        'image': img_src,
        'recommended_tags': pin.recommended_tags,
        'likes': likes_count,
        'is_liked': is_liked,
        'reaction_emoji': my_reaction,
        'is_checked': is_checked,
        'comments': comments_list,
        'created_by': creator_name,
        'creator_username': pin.created_by.username if pin.created_by else '',
        'creator_avatar': creator_avatar,
        'creator_id': pin.created_by.id if pin.created_by else None,
        'created_at': pin.created_at.isoformat()
    }

# Helper: แปลงข้อมูลผู้ใช้ (User Profile) เป็น JSON
def serialize_user(user, current_user=None):
    profile, _ = Profile.objects.get_or_create(user=user)
    followers_count = Follow.objects.filter(following=user).count()
    following_count = Follow.objects.filter(follower=user).count()
    
    is_following = False
    if current_user and current_user.is_authenticated and current_user != user:
        is_following = Follow.objects.filter(follower=current_user, following=user).exists()

    return {
        'id': user.id,
        'username': user.username,
        'display_name': user.first_name or user.username,
        'email': user.email,
        'bio': profile.bio,
        'avatar_url': profile.avatar_url,
        'cover_url': profile.cover_url,
        'followers_count': followers_count,
        'following_count': following_count,
        'is_following': is_following
    }

# --- AUTH APIS (สมัครสมาชิก / เข้าสู่ระบบ / ออกจากระบบ) ---
@csrf_exempt
def api_register(request):
    """ API สำหรับสมัครสมาชิกใหม่ """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        display_name = data.get('display_name', '').strip() or username
        email = data.get('email', '').strip()

        if not username or not password:
            return JsonResponse({'error': 'กรุณากรอกชื่อผู้ใช้และรหัสผ่าน'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'ชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว'}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password, first_name=display_name)
        Profile.objects.create(user=user)
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'user': serialize_user(user, user)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_login(request):
    """ API สำหรับเข้าสู่ระบบ """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({
                'success': True,
                'user': serialize_user(user, user)
            })
        else:
            return JsonResponse({'error': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_logout(request):
    """ API สำหรับออกจากระบบ """
    logout(request)
    return JsonResponse({'success': True})

def api_me(request):
    """ API ตรวจสอบสถานะผู้ใช้ปัจจุบันที่ล็อกอินอยู่ """
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': serialize_user(user, user)
        })
    return JsonResponse({'authenticated': False})

@csrf_exempt
def api_update_profile(request):
    """ API แก้ไขข้อมูลโปรไฟล์ (รูปภาพ, ชื่อ, Bio) """
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return JsonResponse({'error': 'ต้องเข้าสู่ระบบก่อน'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        display_name = data.get('display_name', '').strip()
        bio = data.get('bio', '').strip()
        avatar_url = data.get('avatar_url', '').strip()
        cover_url = data.get('cover_url', '').strip()

        if display_name:
            user.first_name = display_name
            user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        if bio:
            profile.bio = bio
        if avatar_url:
            profile.avatar_url = avatar_url
        if cover_url:
            profile.cover_url = cover_url
        profile.save()

        return JsonResponse({'success': True, 'user': serialize_user(user, user)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --- USER SEARCH & FOLLOW APIS ---
def api_users_search(request):
    """ API ค้นหาผู้ใช้งานระบบตามชื่อหรือ Username """
    query = request.GET.get('q', '').strip()
    current_user = getattr(request, 'user', None)
    
    if not query:
        users = User.objects.all().order_by('-date_joined')[:10]
    else:
        users = User.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query)
        )[:15]

    results = [serialize_user(u, current_user) for u in users]
    return JsonResponse({'users': results})

def api_user_detail(request, user_id):
    """ API ดึงข้อมูลโปรไฟล์ผู้ใช้ พร้อมรายการโพสต์ของผู้ใช้นั้น """
    current_user = getattr(request, 'user', None)
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'ไม่พบผู้ใช้นี้'}, status=404)

    user_info = serialize_user(target_user, current_user)
    user_pins = Pin.objects.filter(created_by=target_user).order_by('-created_at')
    posts = [serialize_pin(p, current_user) for p in user_pins]

    return JsonResponse({'user': user_info, 'posts': posts})

@csrf_exempt
def api_follow_toggle(request, user_id):
    """ API กดติดตาม / เลิกติดตาม ผู้ใช้งาน """
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return JsonResponse({'error': 'ต้องเข้าสู่ระบบก่อน'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'ไม่พบผู้ใช้นี้'}, status=404)

    if target_user == user:
        return JsonResponse({'error': 'ไม่สามารถติดตามตัวเองได้'}, status=400)

    follow_obj, created = Follow.objects.get_or_create(follower=user, following=target_user)
    if not created:
        follow_obj.delete()
        is_following = False
    else:
        is_following = True
        # สร้างการแจ้งเตือนเมื่อมีคนกดติดตาม
        Notification.objects.create(
            recipient=target_user,
            actor=user,
            type='follow',
            message=f"{user.first_name or user.username} เริ่มติดตามคุณแล้ว 🎉"
        )

    followers_count = Follow.objects.filter(following=target_user).count()
    return JsonResponse({'success': True, 'is_following': is_following, 'followers_count': followers_count})

# --- PINS / POSTS APIS ---
@csrf_exempt
def api_pins_list_create(request):
    """ API ดึงรายการโพสต์ทั้งหมด หรือ สร้างโพสต์ใหม่ """
    user = getattr(request, 'user', None)
    if request.method == 'GET':
        pins = Pin.objects.all().order_by('-created_at')
        serialized = [serialize_pin(p, user) for p in pins]
        return JsonResponse({'pins': serialized})
    
    elif request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'กรุณาระบุชื่อสถานที่'}, status=400)
        
        province = request.POST.get('province', 'ศรีสะเกษ').strip()
        district = request.POST.get('district', '').strip()
        village = request.POST.get('village', '').strip()
        category = request.POST.get('category', 'พักผ่อนหย่อนใจ').strip()
        description = request.POST.get('description', '').strip()
        recommended_tags = request.POST.get('recommended_tags', '📸 จุดถ่ายรูปสวย').strip()

        lat_str = request.POST.get('latitude', '')
        lng_str = request.POST.get('longitude', '')
        lat = float(lat_str) if lat_str else None
        lng = float(lng_str) if lng_str else None

        image = request.FILES.get('image')

        pin = Pin.objects.create(
            name=name,
            province=province,
            district=district,
            village=village,
            category=category,
            description=description,
            latitude=lat,
            longitude=lng,
            image=image,
            recommended_tags=recommended_tags,
            created_by=user if (user and user.is_authenticated) else None
        )

        return JsonResponse({'success': True, 'pin': serialize_pin(pin, user)})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def api_pin_like(request, pin_id):
    """ API กดไลก์ / เปลี่ยนรีแอคชันโพสต์ """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        pin = Pin.objects.get(id=pin_id)
    except Pin.DoesNotExist:
        return JsonResponse({'error': 'ไม่พบสถานที่นี้'}, status=404)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        emoji = data.get('emoji', '❤️')
    except Exception:
        emoji = '❤️'

    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return JsonResponse({'success': True, 'likes_count': pin.likes.count() + 1, 'is_liked': True, 'emoji': emoji})

    like_obj, created = PinLike.objects.get_or_create(pin=pin, user=user)
    if not created and like_obj.reaction_emoji == emoji:
        like_obj.delete()
        is_liked = False
        current_emoji = ''
    else:
        like_obj.reaction_emoji = emoji
        like_obj.save()
        is_liked = True
        current_emoji = emoji
        # แจ้งเตือนเจ้าของโพสต์
        if pin.created_by and pin.created_by != user:
            Notification.objects.create(
                recipient=pin.created_by,
                actor=user,
                type='like',
                pin=pin,
                message=f"{user.first_name or user.username} กด {emoji} ถูกใจโพสต์ของคุณ"
            )

    return JsonResponse({
        'success': True,
        'likes_count': pin.likes.count(),
        'is_liked': is_liked,
        'emoji': current_emoji
    })

@csrf_exempt
def api_pin_comment(request, pin_id):
    """ API เพิ่มความคิดเห็นใต้โพสต์ """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        pin = Pin.objects.get(id=pin_id)
    except Pin.DoesNotExist:
        return JsonResponse({'error': 'ไม่พบสถานที่นี้'}, status=404)

    try:
        data = json.loads(request.body.decode('utf-8'))
        text = data.get('text', '').strip()
        emoji = data.get('emoji', '').strip()
        author_name = data.get('name', '').strip()

        if not text and not emoji:
            return JsonResponse({'error': 'กรุณากรอกข้อความคอมเมนต์'}, status=400)

        user = getattr(request, 'user', None)
        active_user = user if (user and user.is_authenticated) else None
        c = PinComment.objects.create(
            pin=pin,
            user=active_user,
            author_name=author_name or (active_user.first_name if active_user else 'ผู้เยี่ยมชม'),
            text=text,
            emoji=emoji
        )

        # แจ้งเตือนเจ้าของโพสต์
        if pin.created_by and active_user and pin.created_by != active_user:
            Notification.objects.create(
                recipient=pin.created_by,
                actor=active_user,
                type='comment',
                pin=pin,
                message=f"{active_user.first_name or active_user.username} คอมเมนต์ในโพสต์ของคุณ: \"{text[:20]}...\""
            )

        return JsonResponse({
            'success': True,
            'comment': {
                'id': c.id,
                'name': c.author_name,
                'avatar': active_user.profile.avatar_url if (active_user and hasattr(active_user, 'profile')) else '',
                'text': c.text,
                'emoji': c.emoji,
                'ts': c.created_at.isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_pin_checkin(request, pin_id):
    """ API กดเช็คอินสถานที่ """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        pin = Pin.objects.get(id=pin_id)
    except Pin.DoesNotExist:
        return JsonResponse({'error': 'ไม่พบสถานที่นี้'}, status=404)

    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return JsonResponse({'success': True, 'is_checked': True})

    checkin_obj, created = PinCheckin.objects.get_or_create(pin=pin, user=user)
    if not created:
        checkin_obj.delete()
        is_checked = False
    else:
        is_checked = True

    return JsonResponse({'success': True, 'is_checked': is_checked})

@csrf_exempt
def api_pin_delete(request, pin_id):
    """ API ลบโพสต์ """
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'error': 'POST or DELETE method required'}, status=405)
    
    try:
        pin = Pin.objects.get(id=pin_id)
    except Pin.DoesNotExist:
        return JsonResponse({'error': 'ไม่พบสถานที่นี้'}, status=404)

    pin.delete()
    return JsonResponse({'success': True})

# --- STORIES APIS ---
@csrf_exempt
def api_stories(request):
    """ API ดึงและเพิ่ม Stories สไตล์ IG/FB """
    user = getattr(request, 'user', None)
    if request.method == 'GET':
        stories = Story.objects.all().order_by('-created_at')[:15]
        res = [
            {
                'id': s.id,
                'user_id': s.user.id,
                'user_name': s.user.first_name or s.user.username,
                'avatar': s.user.profile.avatar_url if hasattr(s.user, 'profile') else '',
                'title': s.title,
                'image_url': s.image_url,
                'created_at': s.created_at.isoformat()
            }
            for s in stories
        ]
        return JsonResponse({'stories': res})
    
    elif request.method == 'POST':
        if not (user and user.is_authenticated):
            return JsonResponse({'error': 'ต้องเข้าสู่ระบบก่อนสร้าง Story'}, status=401)
        
        data = json.loads(request.body.decode('utf-8'))
        title = data.get('title', 'สตอรี่ของฉัน').strip()
        image_url = data.get('image_url', '').strip()

        story = Story.objects.create(user=user, title=title, image_url=image_url)
        return JsonResponse({'success': True, 'story': {
            'id': story.id,
            'user_name': user.first_name or user.username,
            'avatar': user.profile.avatar_url if hasattr(user, 'profile') else '',
            'title': story.title,
            'image_url': story.image_url,
            'created_at': story.created_at.isoformat()
        }})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# --- NOTIFICATIONS APIS ---
def api_notifications(request):
    """ API ดึงรายการแจ้งเตือนสำหรับผู้ใช้ที่เข้าสู่ระบบอยู่ """
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return JsonResponse({'notifications': []})

    notes = Notification.objects.filter(recipient=user).order_by('-created_at')[:20]
    res = [
        {
            'id': n.id,
            'actor_name': n.actor.first_name or n.actor.username,
            'actor_avatar': n.actor.profile.avatar_url if hasattr(n.actor, 'profile') else '',
            'type': n.type,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        }
        for n in notes
    ]
    return JsonResponse({'notifications': res})

@csrf_exempt
def api_notifications_read(request):
    """ API ทำเครื่องหมายว่าอ่านแจ้งเตือนแล้ว """
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})
