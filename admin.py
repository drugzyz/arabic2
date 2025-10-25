# [file name]: admin.py
# -*- coding: utf-8 -*-

# بلجن إدارة المالكين والإعدادات

# المتغيرات العالمية
send_msg = None
get_user_permission_level = None
get_affiliation = None
is_owner = None
db_execute = None
db_fetchall = None
clean_jid = None
client = None
xmpp = None
megabase = None
get_level = None
get_role = None
get_user_jid = None

def init_plugin(global_vars):
    """تهيئة البلجن بالمتغيرات العالمية"""
    global send_msg, get_user_permission_level, get_affiliation, is_owner, db_execute, db_fetchall, clean_jid
    global client, xmpp, megabase, get_level, get_role, get_user_jid
    
    # استيراد الدوال من النظام الرئيسي
    send_msg = global_vars.get('send_msg')
    get_user_permission_level = global_vars.get('get_user_permission_level')
    get_affiliation = global_vars.get('get_affiliation')
    is_owner = global_vars.get('is_owner')
    db_execute = global_vars.get('db_execute')
    db_fetchall = global_vars.get('db_fetchall')
    clean_jid = global_vars.get('clean_jid')
    client = global_vars.get('client')
    megabase = global_vars.get('megabase')
    get_level = global_vars.get('get_level')
    get_role = global_vars.get('get_role')
    get_user_jid = global_vars.get('get_user_jid')
    
    # استيراد xmpp مباشرة
    import xmpp
    globals()['xmpp'] = xmpp
    
    print("✅ تم تهيئة بلجن الإدارة")

def join_room(msg_type, jid, nick, text):
    """الانضمام إلى غرفة عامة"""
    if not is_owner(jid):
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
    
    if not text.strip():
        send_msg(msg_type, jid, nick, "❌ يرجى إدخال اسم الغرفة: !انضمام room@conference.example.com")
        return
    
    room_jid = text.strip()
    
    # التأكد من صيغة الغرفة
    if not room_jid or '@' not in room_jid:
        send_msg(msg_type, jid, nick, "❌ صيغة JID الغرفة غير صحيحة")
        return
    
    try:
        if client is None:
            send_msg(msg_type, jid, nick, "❌ البوت غير متصل حالياً")
            return
        
        # إرسال طلب حضور للانضمام إلى الغرفة
        pres = xmpp.Presence(to=room_jid)
        client.send(pres)
        
        # إضافة الغرفة إلى قاعدة البيانات للإلتحاق التلقائي مستقبلاً
        db_execute(
            'INSERT OR REPLACE INTO rooms (room, auto_join) VALUES (?, ?)',
            (room_jid, 1)
        )
        
        send_msg(msg_type, jid, nick, f"✅ تم إرسال طلب الانضمام إلى الغرفة: {room_jid}")
        send_msg(msg_type, jid, nick, "⏳ جاري الانضمام... قد يستغرق بضع ثوانٍ")
        
    except Exception as e:
        error_msg = f"❌ خطأ في الانضمام إلى الغرفة: {str(e)}"
        send_msg(msg_type, jid, nick, error_msg)

def leave_room(msg_type, jid, nick, text):
    """مغادرة غرفة"""
    if not is_owner(jid):
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
    
    if not text.strip():
        # إذا لم يتم تحديد غرفة، مغادرة الغرفة الحالية
        if '/' in jid:
            room_jid = jid.split('/')[0]
        else:
            send_msg(msg_type, jid, nick, "❌ يرجى إدخال اسم الغرفة: !مغادرة room@conference.example.com")
            return
    else:
        room_jid = text.strip()
    
    try:
        if client is None:
            send_msg(msg_type, jid, nick, "❌ البوت غير متصل حالياً")
            return
        
        # إرسال طلب حضور بمغادرة الغرفة
        pres = xmpp.Presence(to=room_jid, typ='unavailable')
        client.send(pres)
        
        # إزالة الغرفة من قاعدة البيانات لمنع الإلتحاق التلقائي مستقبلاً
        db_execute('DELETE FROM rooms WHERE room = ?', (room_jid,))
        
        send_msg(msg_type, jid, nick, f"✅ تم مغادرة الغرفة: {room_jid}")
        
    except Exception as e:
        error_msg = f"❌ خطأ في مغادرة الغرفة: {str(e)}"
        send_msg(msg_type, jid, nick, error_msg)

def kick_user(msg_type, jid, nick, text):
    """طرد مستخدم من الغرفة"""
    if not text:
        send_msg(msg_type, jid, nick, "❌ يرجى إدخال اسم المستخدم المراد طرده")
        return
    
    user_level = get_level(jid, nick)
    if user_level < 7:  # مشرف أو أعلى
        send_msg(msg_type, jid, nick, "❌ تحتاج إلى صلاحية مشرف أو أعلى")
        return
    
    target = text.strip()
    reason = "تم الطرد بواسطة المشرف"
    
    try:
        if client is None:
            send_msg(msg_type, jid, nick, "❌ البوت غير متصل حالياً")
            return
            
        room_jid = jid.split('/')[0] if '/' in jid else jid
        iq = xmpp.Iq(typ='set', to=room_jid)
        query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
        item = query.setTag('item', {'nick': target, 'role': 'none'})
        item.setTagData('reason', reason)
        client.send(iq)
        
        send_msg(msg_type, jid, nick, f"✅ تم طرد المستخدم: {target}")
        
    except Exception as e:
        error_msg = f"❌ خطأ في طرد المستخدم: {str(e)}"
        send_msg(msg_type, jid, nick, error_msg)

def ban_user(msg_type, jid, nick, text):
    """حظر مستخدم من الغرفة"""
    if not text:
        send_msg(msg_type, jid, nick, "❌ يرجى إدخال JID المستخدم المراد حظره")
        return
    
    user_level = get_level(jid, nick)
    if user_level < 8:  # مالك الغرفة فقط
        send_msg(msg_type, jid, nick, "❌ تحتاج إلى صلاحية مالك الغرفة")
        return
    
    target_jid = text.strip()
    reason = "تم الحظر بواسطة المالك"
    
    # التحقق من صيغة JID
    if '@' not in target_jid:
        send_msg(msg_type, jid, nick, "❌ صيغة JID غير صحيحة")
        return
    
    try:
        if client is None:
            send_msg(msg_type, jid, nick, "❌ البوت غير متصل حالياً")
            return
            
        room_jid = jid.split('/')[0] if '/' in jid else jid
        iq = xmpp.Iq(typ='set', to=room_jid)
        query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
        item = query.setTag('item', {'affiliation': 'outcast', 'jid': target_jid})
        item.setTagData('reason', reason)
        client.send(iq)
        
        send_msg(msg_type, jid, nick, f"✅ تم حظر المستخدم: {target_jid}")
        
    except Exception as e:
        error_msg = f"❌ خطأ في حظر المستخدم: {str(e)}"
        send_msg(msg_type, jid, nick, error_msg)

def unban_user(msg_type, jid, nick, text):
    """إزالة حظر مستخدم من الغرفة"""
    if not text:
        send_msg(msg_type, jid, nick, "❌ يرجى إدخال JID المستخدم المراد إزالة الحظر عنه")
        return
    
    user_level = get_level(jid, nick)
    if user_level < 8:  # مالك الغرفة فقط
        send_msg(msg_type, jid, nick, "❌ تحتاج إلى صلاحية مالك الغرفة")
        return
    
    target_jid = text.strip()
    
    try:
        if client is None:
            send_msg(msg_type, jid, nick, "❌ البوت غير متصل حالياً")
            return
            
        room_jid = jid.split('/')[0] if '/' in jid else jid
        iq = xmpp.Iq(typ='set', to=room_jid)
        query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
        item = query.setTag('item', {'affiliation': 'none', 'jid': target_jid})
        client.send(iq)
        
        send_msg(msg_type, jid, nick, f"✅ تم إزالة حظر المستخدم: {target_jid}")
        
    except Exception as e:
        error_msg = f"❌ خطأ في إزالة الحظر: {str(e)}"
        send_msg(msg_type, jid, nick, error_msg)

def mute_user(msg_type, jid, nick, text):
    """كتم مستخدم في الغرفة"""
    if not text:
        send_msg(msg_type, jid, nick, "❌ يرجى إدخال اسم المستخدم المراد كتمه")
        return
    
    user_level = get_level(jid, nick)
    if user_level < 7:  # مشرف أو أعلى
        send_msg(msg_type, jid, nick, "❌ تحتاج إلى صلاحية مشرف أو أعلى")
        return
    
    target = text.strip()
    
    try:
        if client is None:
            send_msg(msg_type, jid, nick, "❌ البوت غير متصل حالياً")
            return
            
        room_jid = jid.split('/')[0] if '/' in jid else jid
        iq = xmpp.Iq(typ='set', to=room_jid)
        query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
        item = query.setTag('item', {'nick': target, 'role': 'visitor'})
        client.send(iq)
        
        send_msg(msg_type, jid, nick, f"✅ تم كتم المستخدم: {target}")
        
    except Exception as e:
        error_msg = f"❌ خطأ في كتم المستخدم: {str(e)}"
        send_msg(msg_type, jid, nick, error_msg)

def unmute_user(msg_type, jid, nick, text):
    """إزالة كتم مستخدم في الغرفة"""
    if not text:
        send_msg(msg_type, jid, nick, "❌ يرجى إدخال اسم المستخدم المراد إزالة الكتم عنه")
        return
    
    user_level = get_level(jid, nick)
    if user_level < 7:  # مشرف أو أعلى
        send_msg(msg_type, jid, nick, "❌ تحتاج إلى صلاحية مشرف أو أعلى")
        return
    
    target = text.strip()
    
    try:
        if client is None:
            send_msg(msg_type, jid, nick, "❌ البوت غير متصل حالياً")
            return
            
        room_jid = jid.split('/')[0] if '/' in jid else jid
        iq = xmpp.Iq(typ='set', to=room_jid)
        query = iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
        item = query.setTag('item', {'nick': target, 'role': 'participant'})
        client.send(iq)
        
        send_msg(msg_type, jid, nick, f"✅ تم إزالة كتم المستخدم: {target}")
        
    except Exception as e:
        error_msg = f"❌ خطأ في إزالة الكتم: {str(e)}"
        send_msg(msg_type, jid, nick, error_msg)

def refresh_lists(msg_type, jid, nick, text):
    """تحديث قوائم المستخدمين يدوياً"""
    if not is_owner(jid):
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
    
    # إرسال طلب للحصول على قائمة المستخدمين
    try:
        if client is None:
            send_msg(msg_type, jid, nick, "❌ البوت غير متصل حالياً")
            return
            
        room_jid = jid.split('/')[0] if '/' in jid else jid
        iq = xmpp.Iq(typ='get', to=room_jid)
        iq.setTag('query', namespace=xmpp.NS_MUC_ADMIN)
        client.send(iq)
        
        send_msg(msg_type, jid, nick, "🔄 جاري تحديث قوائم المستخدمين...")
    except Exception as e:
        error_msg = f"❌ خطأ في تحديث القوائم: {str(e)}"
        send_msg(msg_type, jid, nick, error_msg)

def user_permissions(msg_type, jid, nick, text):
    """عرض صلاحيات المستخدم الحالي"""
    if not text:
        target_nick = nick
        target_jid = jid
    else:
        target_nick = text.strip()
        target_jid = jid
    
    user_level = get_level(target_jid, target_nick)
    affiliation = get_affiliation(target_jid, target_nick)
    role = get_role(target_jid, target_nick)
    
    level_names = {
        1: "مستخدم عادي",
        5: "عضو",
        6: "مدير",
        7: "مشرف", 
        8: "مالك غرفة",
        10: "مالك بوت"
    }
    
    level_name = level_names.get(user_level, "غير معروف")
    
    msg = f"""🔰 صلاحيات المستخدم {target_nick}:

• مستوى الصلاحية: {user_level} ({level_name})
• الصلاحية في الغرفة: {affiliation}
• الدور في الغرفة: {role}
• JID: {clean_jid(f"{target_jid}/{target_nick}" if '/' in target_jid else target_jid)}"""
    
    send_msg(msg_type, jid, nick, msg)

def room_info(msg_type, jid, nick, text):
    """عرض معلومات عن الغرفة الحالية"""
    room = jid.split('/')[0] if '/' in jid else jid
    
    # عدد المستخدمين
    users_count = len([u for u in megabase if u[0] == room])
    
    # المالكين والمشرفين
    owners = [u[1] for u in megabase if u[0] == room and u[2] == 'owner']
    admins = [u[1] for u in megabase if u[0] == room and u[2] == 'admin']
    members = [u[1] for u in megabase if u[0] == room and u[2] == 'member']
    
    msg = f"""🏠 معلومات الغرفة: {room}

• عدد المستخدمين: {users_count}
• المالكين: {', '.join(owners) if owners else 'لا يوجد'}
• المشرفين: {', '.join(admins) if admins else 'لا يوجد'}
• الأعضاء: {len(members)} عضو"""

    send_msg(msg_type, jid, nick, msg)

def room_settings(msg_type, jid, nick, text):
    """عرض إعدادات الغرفة الحالية"""
    room = jid.split('/')[0] if '/' in jid else jid
    
    # الحصول على إعدادات الغرفة
    private_lock = db_fetchone(
        'SELECT value FROM plugin_data WHERE plugin=? AND key=?',
        ('muc_config', f'{room}:private_messages_locked')
    )
    
    private_status = "مقفولة" if private_lock and private_lock['value'] == '1' else "مفتوحة"
    
    # حساب عدد الأوامر المتاحة
    available_commands = len([cmd for cmd in execute() if get_level(jid, nick) >= cmd[0]])
    
    msg = f"""⚙️ إعدادات الغرفة: {room}

• الرسائل الخاصة: {private_status}
• عدد الأوامر المتاحة: {available_commands}
• حالة البوت: ✅ نشط"""

    send_msg(msg_type, jid, nick, msg)

def list_rooms(msg_type, jid, nick, text):
    """عرض قائمة الغرف التي ينضم إليها البوت"""
    if not is_owner(jid):
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
    
    rooms = db_fetchall('SELECT room, auto_join FROM rooms ORDER BY room')
    
    if rooms:
        room_list = []
        for room in rooms:
            status = "تلقائي" if room['auto_join'] else "يدوي"
            room_list.append(f"• {room['room']} ({status})")
        
        msg = "🏠 قائمة غرف البوت:\n" + "\n".join(room_list)
    else:
        msg = "❌ البوت غير منضم لأي غرف"
    
    send_msg(msg_type, jid, nick, msg)

def add_owner(msg_type, jid, nick, text):
    """إضافة مالك جديد"""
    user_level = get_user_permission_level(jid, nick, jid.split('/')[0] if '/' in jid else "")
    
    if user_level < 10:  # يحتاج صلاحية مالك
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
    
    if not text.strip():
        send_msg(msg_type, jid, nick, "❌ يرجى تحديد JID المستخدم: !مالك user@example.com")
        return
    
    target_jid = clean_jid(text.strip())
    
    # إضافة المالك
    from database import add_owner as db_add_owner
    if db_add_owner(target_jid, nick):
        send_msg(msg_type, jid, nick, f"✅ تم إضافة المالك: {target_jid}")
    else:
        send_msg(msg_type, jid, nick, f"❌ فشل في إضافة المالك: {target_jid}")

def remove_owner(msg_type, jid, nick, text):
    """إزالة مالك"""
    user_level = get_user_permission_level(jid, nick, jid.split('/')[0] if '/' in jid else "")
    
    if user_level < 10:
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
    
    if not text.strip():
        send_msg(msg_type, jid, nick, "❌ يرجى تحديد JID المستخدم: !حذف_مالك user@example.com")
        return
    
    target_jid = clean_jid(text.strip())
    
    # منع حذف النفس
    current_jid = clean_jid(f"{jid}/{nick}" if '/' in jid else jid)
    if target_jid == current_jid:
        send_msg(msg_type, jid, nick, "❌ لا يمكنك حذف نفسك")
        return
    
    # إزالة المالك
    from database import remove_owner as db_remove_owner
    if db_remove_owner(target_jid):
        send_msg(msg_type, jid, nick, f"✅ تم إزالة المالك: {target_jid}")
    else:
        send_msg(msg_type, jid, nick, f"❌ فشل في إزالة المالك: {target_jid}")

def list_owners(msg_type, jid, nick, text):
    """عرض قائمة المالكين"""
    user_level = get_user_permission_level(jid, nick, jid.split('/')[0] if '/' in jid else "")
    
    if user_level < 10:
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
    
    from database import list_owners as db_list_owners
    owners = db_list_owners()
    
    if not owners:
        send_msg(msg_type, jid, nick, "📋 لا يوجد مالكين مسجلين")
        return
    
    owners_list = "📋 **قائمة المالكين:**\n\n"
    for owner in owners:
        owners_list += f"• {owner['jid']}\n"
        owners_list += f"  ⏰ {owner['added_at']}\n"
        owners_list += f"  👤 بواسطة: {owner['added_by']}\n\n"
    
    send_msg(msg_type, jid, nick, owners_list.strip())

def set_permission(msg_type, jid, nick, text):
    """تعيين صلاحية مستخدم"""
    user_level = get_user_permission_level(jid, nick, jid.split('/')[0] if '/' in jid else "")
    
    if user_level < 10:
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
    
    parts = text.strip().split()
    if len(parts) < 2:
        send_msg(msg_type, jid, nick, "❌ صيغة الأمر: !صلاحية [jid] [مستوى]")
        send_msg(msg_type, jid, nick, "📊 مستويات الصلاحية: 1=عادي, 6=عضو, 7=مشرف, 8=مالك غرفة, 9=مالك بوت")
        return
    
    target_jid = clean_jid(parts[0])
    try:
        level = int(parts[1])
        if level < 1 or level > 10:
            raise ValueError
    except ValueError:
        send_msg(msg_type, jid, nick, "❌ مستوى الصلاحية يجب أن يكون رقماً بين 1 و 9")
        return
    
    room = jid.split('/')[0] if '/' in jid else ""
    
    from database import set_user_permission
    if set_user_permission(target_jid, room, level, nick):
        send_msg(msg_type, jid, nick, f"✅ تم تعيين صلاحية {level} للمستخدم: {target_jid}")
    else:
        send_msg(msg_type, jid, nick, f"❌ فشل في تعيين الصلاحية: {target_jid}")

def execute():
    """الدالة الرئيسية لتحميل الأوامر"""
    
    commands = [
        # أوامر المالكين (مستوى 10)
        (10, 'مالك', add_owner, 1, 'إضافة مالك جديد - !مالك [jid]'),
        (10, 'حذف_مالك', remove_owner, 1, 'إزالة مالك - !حذف_مالك [jid]'),
        (10, 'قائمة_المالكين', list_owners, 0, 'عرض قائمة المالكين - !قائمة_المالكين'),
        (10, 'صلاحية', set_permission, 2, 'تعيين صلاحية مستخدم - !صلاحية [jid] [مستوى]'),
        (10, 'قائمة_الغرف', list_rooms, 0, 'عرض قائمة غرف البوت'),
        (10, 'تحديث_القوائم', refresh_lists, 0, 'تحديث قوائم المستخدمين يدوياً'),
        (8, 'انضمام', join_room, 1, 'الانضمام إلى غرفة عامة - !انضمام [room@conference.example.com]'),
        (8, 'مغادرة', leave_room, 1, 'مغادرة غرفة - !مغادرة [room@conference.example.com]'),
        
        # أوامر إدارة الغرف (مستوى 7-8)
        (7, 'طرد', kick_user, 1, 'طرد مستخدم من الغرفة: !طرد [اسم المستخدم]'),
        (8, 'حظر', ban_user, 1, 'حظر مستخدم من الغرفة: !حظر [jid المستخدم]'),
        (8, 'ازالة_حظر', unban_user, 1, 'إزالة حظر مستخدم: !ازالة_حظر [jid المستخدم]'),
        (7, 'كتم', mute_user, 1, 'كتم مستخدم في الغرفة: !كتم [اسم المستخدم]'),
        (7, 'ازالة_كتم', unmute_user, 1, 'إزالة كتم مستخدم: !ازالة_كتم [اسم المستخدم]'),
        
        (1, 'صلاحيات_المستخدم', user_permissions, 1, 'عرض صلاحيات مستخدم: !صلاحيات_المستخدم [اسم المستخدم]'),
        (1, 'معلومات_الغرفة', room_info, 0, 'عرض معلومات عن الغرفة الحالية'),
        (1, 'اعدادات_الغرفة', room_settings, 0, 'عرض إعدادات الغرفة الحالية'),
    ]
    
    print("✅ تم تحميل بلجن الإدارة والصلاحيات (admin.py)")
    return commands

# دوال يمكن استدعاؤها من run.py الرئيسي
def get_message_handlers():
    """إرجاع معالجات الرسائل"""
    return []  # لا توجد معالجات رسائل في هذا البلجن

def get_presence_handlers():
    """إرجاع معالجات الحضور"""
    return []  # لا توجد معالجات حضور في هذا البلجن

def get_iq_handlers():
    """إرجاع معالجات IQ"""
    return []  # لا توجد معالجات IQ في هذا البلجن

def get_timer_functions():
    """إرجاع دوال المؤقت"""
    return []  # لا توجد دوال مؤقت في هذا البلجن

print("✅ تم تحميل بلجن الإدارة والصلاحيات مع دعم النظام الجديد")