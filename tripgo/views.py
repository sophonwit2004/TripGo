import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Pin, PinLike, PinComment, PinCheckin

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
        'created_by': pin.created_by.first_name or pin.created_by.username if pin.created_by else 'ผู้ใช้ TripGo',
        'created_at': pin.created_at.isoformat()
    }

@csrf_exempt
def api_register(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        display_name = data.get('display_name', '').strip() or username

        if not username or not password:
            return JsonResponse({'error': 'กรุณากรอกชื่อผู้ใช้และรหัสผ่าน'}, status=400)
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'ชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว'}, status=400)

        user = User.objects.create_user(username=username, password=password, first_name=display_name)
        login(request, user)
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'display_name': user.first_name or user.username
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_login(request):
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
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'display_name': user.first_name or user.username
                }
            })
        else:
            return JsonResponse({'error': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_logout(request):
    logout(request)
    return JsonResponse({'success': True})

def api_me(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'display_name': user.first_name or user.username
            }
        })
    return JsonResponse({'authenticated': False})

@csrf_exempt
def api_pins_list_create(request):
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
        # Fallback for anonymous users
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

    return JsonResponse({
        'success': True,
        'likes_count': pin.likes.count(),
        'is_liked': is_liked,
        'emoji': current_emoji
    })

@csrf_exempt
def api_pin_comment(request, pin_id):
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

        return JsonResponse({
            'success': True,
            'comment': {
                'id': c.id,
                'name': c.author_name,
                'text': c.text,
                'emoji': c.emoji,
                'ts': c.created_at.isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_pin_checkin(request, pin_id):
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
    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'error': 'POST or DELETE method required'}, status=405)
    
    try:
        pin = Pin.objects.get(id=pin_id)
    except Pin.DoesNotExist:
        return JsonResponse({'error': 'ไม่พบสถานที่นี้'}, status=404)

    pin.delete()
    return JsonResponse({'success': True})

