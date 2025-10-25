# -*- coding: utf-8 -*-

send_msg = None

def init_plugin(global_vars):
    global send_msg
    send_msg = global_vars.get('send_msg')
    print("✅ تم تحميل بلجن الاختبار")

def اختبار(msg_type, jid, nick, text):
    """اختبار إرسال الرسائل"""
    try:
        send_msg(msg_type, jid, nick, "🔊 اختبار صوتي: البوت يستقبل ويستجيب!")
        send_msg(msg_type, jid, nick, f"📊 معلومات الجلسة: نوع={msg_type}, غرفة={jid}, مستخدم={nick}")
        
        if msg_type == 'groupchat':
            send_msg(msg_type, jid, nick, "📍 هذه رسالة جماعية في الغرفة")
        else:
            send_msg(msg_type, jid, nick, "🔒 هذه رسالة خاصة")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار الإرسال: {e}")

def execute():
    return [
        (1, 'اختبار', اختبار, 0, 'اختبار إرسال الرسائل - !اختبار'),
    ]

presence_control = []
message_act_control = []
iq_control = []
timer_functions = []