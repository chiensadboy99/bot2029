import logging
import json
import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ParseMode
from datetime import timedelta
import pytz
import hashlib
import math
from collections import Counter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from keep_alive import keep_alive

# === CẤU HÌNH ===
# Lấy token từ biến môi trường (an toàn hơn)
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    # Fallback cho local test (không nên dùng trên Railway)
    TOKEN = "8684463452:AAF63cKhatW3kk1ZLORZEfN6j7kzfGQjLiI"
    print("⚠️ CẢNH BÁO: Đang dùng token hardcode, không an toàn!")

ADMIN_ID = int(os.environ.get("ADMIN_ID", 7071414779))

# Khởi tạo scheduler
scheduler = AsyncIOScheduler(timezone=pytz.UTC)

# Dictionary lưu users đã kích hoạt (RAM cache)
activated_users = {}
active_users = {}  # Dùng cho schedule_deactivation

# Đảm bảo thư mục data tồn tại
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DATA_FILE = os.path.join(DATA_DIR, "activated_users.json")

# Load dữ liệu từ file
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        activated_users = json.load(f)
        print(f"✅ Đã load {len(activated_users)} users từ file")
except FileNotFoundError:
    print("📝 Không tìm thấy file data, tạo mới...")
    activated_users = {}
except json.JSONDecodeError:
    print("❌ Lỗi đọc file JSON, tạo mới...")
    activated_users = {}

# Gán quyền vĩnh viễn cho ADMIN_ID
activated_users[str(ADMIN_ID)] = {"expires": "vĩnh viễn"}

def save_activated_users():
    """Lưu dữ liệu users ra file"""
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(DATA_DIR, exist_ok=True)
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(activated_users, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu {len(activated_users)} users")
        return True
    except Exception as e:
        print(f"❌ Lỗi lưu file: {e}")
        return False

def is_admin(user_id):
    return user_id == ADMIN_ID

def check_user(user_id):
    """Kiểm tra user có được kích hoạt không"""
    try:
        user_id_str = str(user_id)
        
        if user_id_str not in activated_users:
            return False, None
        
        expire_info = activated_users[user_id_str]
        expire = expire_info["expires"]
        
        if expire == "vĩnh viễn":
            return True, "vĩnh viễn"
        
        # Parse thời gian hết hạn
        timezone = pytz.timezone("Asia/Ho_Chi_Minh")
        exp_date = datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
        exp_date = timezone.localize(exp_date)
        
        # Lấy thời gian hiện tại
        now = datetime.now(timezone)
        
        if now < exp_date:
            return True, expire
        else:
            # Xóa user đã hết hạn
            del activated_users[user_id_str]
            save_activated_users()
            return False, expire
            
    except Exception as e:
        print(f"Lỗi check_user: {e}")
        return False, None

# Khởi tạo bot
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Khởi động scheduler
scheduler.start()

def schedule_deactivation(user_id: int, hours: int):
    """Lên lịch hủy kích hoạt user sau số giờ"""
    run_time = datetime.now(pytz.utc) + timedelta(hours=hours)
    job_id = f"deactivate_{user_id}"
    
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    # Tạo coroutine function để chạy
    async def deactivate_wrapper():
        await deactivate_user(user_id)
    
    scheduler.add_job(
        deactivate_wrapper,
        trigger=DateTrigger(run_date=run_time, timezone=pytz.utc),
        id=job_id
    )

async def deactivate_user(user_id: int):
    """Hủy kích hoạt user"""
    user_id_str = str(user_id)
    if user_id_str in activated_users:
        del activated_users[user_id_str]
        save_activated_users()
        try:
            await bot.send_message(user_id, "⏰ Thời hạn sử dụng đã hết. Bot của bạn đã bị hủy kích hoạt.")
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn hủy kích hoạt: {e}")

def generate_sha224(md5_hash):
    return hashlib.sha224(md5_hash.encode('utf-8')).hexdigest()

def calculate_entropy(md5_hash):
    freq = Counter(md5_hash)
    prob = [freq[char] / len(md5_hash) for char in freq]
    entropy = -sum(p * math.log2(p) for p in prob)
    return round(entropy, 4)

def geometric_mean(values):
    product = 1
    for value in values:
        product *= value
    return product ** (1 / len(values))

def bit_1_ratio(md5_hash):
    binary_rep = bin(int(md5_hash, 16))[2:].zfill(128)
    return binary_rep.count("1") / len(binary_rep)

def hex_greater_than_8_ratio(md5_hash):
    return sum(1 for char in md5_hash if int(char, 16) >= 8) / len(md5_hash)

def standard_deviation(values):
    if not values:
        return 0
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))

def fibonacci_mod(x, mod):
    if x < 0:
        return 0
    fib = [0, 1]
    while len(fib) <= x:
        fib.append(fib[-1] + fib[-2])
    return fib[x] % mod

def analyze_md5_advanced(md5_hash):
    hex_pairs = [int(md5_hash[i:i+2], 16) for i in range(0, len(md5_hash), 2)]
    md5_int = int(md5_hash, 16)

    digits_sum = sum(int(char, 16) for char in md5_hash)
    hex_sum = sum(hex_pairs)
    binary_ones = bin(md5_int).count("1")
    bit_1_percentage = bit_1_ratio(md5_hash)
    hex_greater_than_8 = hex_greater_than_8_ratio(md5_hash)
    
    xor_value = 0
    for value in hex_pairs:
        xor_value ^= value

    lucas = [2, 1]
    for _ in range(14):
        lucas.append(lucas[-1] + lucas[-2])
    lucas_weighted_sum = sum(a * b for a, b in zip(hex_pairs[:15], lucas[:15]))

    hex_std_dev = standard_deviation(hex_pairs)
    complexity = len(set(md5_hash))
    fourier_energy = sum(abs(hex_pairs[i] - hex_pairs[i - 1]) for i in range(1, len(hex_pairs)))

    sha224_hash = generate_sha224(md5_hash)
    sha224_sum = sum(int(sha224_hash[i:i+2], 16) for i in range(0, len(sha224_hash), 2))

    first_half, second_half = md5_hash[:16], md5_hash[16:]
    symmetry_score = sum(1 for i in range(16) if first_half[i] == second_half[i])
    geometric_mean_value = geometric_mean(hex_pairs)
    combined_xor = xor_value ^ int(sha224_hash[:2], 16)
    fibonacci_score = fibonacci_mod(digits_sum, 100)

    blake2b_xor = 0
    for i in range(0, len(sha224_hash), 2):
        blake2b_xor ^= int(sha224_hash[i:i+2], 16)

    weighted_edge = (hex_pairs[0] * 3 + hex_pairs[-1] * 2) % 100
    prime_mods = [43, 47, 53, 59, 61, 67]
    mod_values = [hex_sum % prime for prime in prime_mods]
    max_repeating_char = max(md5_hash.count(char) for char in set(md5_hash))
    odd_chars = sum(1 for char in md5_hash if int(char, 16) % 2 == 1)
    middle_bytes = sum(hex_pairs[len(hex_pairs)//4: 3*len(hex_pairs)//4])
    fibo_in_md5 = sum(1 for char in md5_hash if char in '12358')
    sha1_symmetry = sum(1 for i in range(16) if sha224_hash[i] == sha224_hash[39-i])
    entropy = calculate_entropy(md5_hash)
    total_xor = xor_value ^ blake2b_xor ^ combined_xor
    last_digit = int(md5_hash[-1], 16)

    total_score = (
        digits_sum * 0.05 + hex_sum * 0.05 + binary_ones * 0.05 +
        bit_1_percentage * 0.1 + hex_greater_than_8 * 0.1 + lucas_weighted_sum * 0.05 +
        hex_std_dev * 0.05 + complexity * 0.05 + fourier_energy * 0.05 +
        sha224_sum * 0.05 + symmetry_score * 0.05 + geometric_mean_value * 0.05 +
        combined_xor * 0.05 + fibonacci_score * 0.05 + blake2b_xor * 0.05 +
        weighted_edge * 0.05 + sum(mod_values) * 0.05 + max_repeating_char * 0.05 +
        odd_chars * 0.05 + middle_bytes * 0.05 + fibo_in_md5 * 0.05 +
        sha1_symmetry * 0.05 + entropy * 0.05 + total_xor * 0.05 +
        last_digit * 0.05
    ) % 100

    return {
        "tai": round(total_score, 2),
        "xiu": round(100 - total_score, 2),
        "last_digit": last_digit,
        "bit_1_percentage": round(bit_1_percentage * 100, 2),
        "hex_8_percentage": round(hex_greater_than_8 * 100, 2),
        "hex_std_dev": round(hex_std_dev, 2),
        "entropy": round(entropy, 4),
    }

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    ok, exp = check_user(message.from_user.id)
    if not ok:
        await message.reply("🎲 Chào mừng bạn đã đến với tts tool \n❌ Bạn chưa được cấp quyền sử dụng bot. liên hệ admin để đươc cấp quyền!\n\n Sử dụng lệnh /help để biết thêm chi tiết!")
        return
    await message.reply("🎲 Chào mừng bạn đã đến với md5 tool!\n 🎲 Bạn có thể gửi một chuỗi MD5 để tôi phân tích giúp bạn.\nVí dụ: c54954fc1fcaa22a372b618eea9cb9bd")

@dp.message_handler(commands=["help"])
async def help_cmd(message: types.Message):
    is_ad = is_admin(message.from_user.id)
    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    text = "🌟 TRỢ GIÚP BOT NTT PREMIUM 🌟\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "📋 Danh sách lệnh cơ bản:\n"
    text += "🔹 /start - Khởi động bot và bắt đầu phân tích\n"
    text += "🔹 /id - Xem thông tin ID của bạn\n"
    text += "🔹 /help -  Hiển thị menu trợ giúp này\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    if is_ad:
        text += "👑 QUẢN TRỊ VIÊN ĐẶC QUYỀN 👑\n"
        text += "🔧 Các Lệnh Quản Lý:\n"
        text += "✅ /adduser <id> <số ngày|infinity>\n"
        text += "❌ /removeuser <id>\n"
        text += "📢 /broadcast <nội dung>\n"
        text += "🗓 /danhsach - Danh sách người dùng\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "ℹ️ Gửi chuỗi MD5 (32 ký tự) để phân tích ngay!\n"
    text += "📞 Liên hệ hỗ trợ: https://t.me/NguyenTung2029"
    await message.reply(text)

@dp.message_handler(commands=["id"])
async def id_cmd(message: types.Message):
    uid = message.from_user.id
    name = message.from_user.full_name
    is_ad = is_admin(uid)
    ok, exp = check_user(uid)
    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    status = "👑 Admin" if is_ad else ("✅ Đã kích hoạt" if ok else "❌ Chưa kích hoạt")
    text = [
        "🆔 THÔNG TIN NGƯỜI DÙNG 🆔",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"👤 Tên: {name}",
        f"🔢 ID: {uid}",
        f"📊 Trạng Thái: {status}",
        f"⏰ Hạn Dùng: {exp if exp else 'Không có'}",
        f"⏰ Thời gian kiểm tra: {now_str}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📞 Liên hệ: https://t.me/NguyenTung2029"
    ]
    await message.reply("\n".join(text))

# === ADMIN: ADD USER ===
@dp.message_handler(commands=["adduser"])
async def add_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ Bạn không có quyền.")
        
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("❗ Dùng: /adduser <id> <số ngày|infinity>")

    user_id = parts[1]
    days = parts[2]
    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")

    if days == "infinity":
        activated_users[user_id] = {"expires": "vĩnh viễn"}
        save_activated_users()
        await message.reply(f"✅ Đã cấp quyền vĩnh viễn cho ID {user_id}\n\n⏰ Thời gian cấp: {now_str}")
    else:
        try:
            days = int(days)
            timezone = pytz.timezone("Asia/Ho_Chi_Minh")
            expire_time = datetime.now(timezone) + timedelta(days=days)
            expire_str = expire_time.strftime("%Y-%m-%d %H:%M:%S")
            activated_users[user_id] = {"expires": expire_str}
            save_activated_users()
            await message.reply(f"✅ Đã cấp quyền {days} ngày cho ID {user_id}\n📅 Hết hạn: {expire_str}\n\n⏰ Thời gian cấp: {now_str}")
        except ValueError:
            return await message.reply("❗ Số ngày không hợp lệ.")

# === ADMIN: REMOVE USER ===
@dp.message_handler(commands=["removeuser"])
async def remove_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ Bạn không có quyền.")
    
    parts = message.text.split()
    if len(parts) != 2:
        return await message.reply("❗ Dùng: /removeuser <id>")

    user_id = parts[1]
    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    
    if user_id in activated_users:
        del activated_users[user_id]
        save_activated_users()
        await message.reply(f"❌ Đã xóa quyền của ID {user_id}\n\n⏰ Thời gian xóa: {now_str}")
    else:
        await message.reply("⚠️ ID không tồn tại trong danh sách")

# === ADMIN: BROADCAST ===
@dp.message_handler(commands=["broadcast"])
async def broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ Bạn không có quyền.")
    
    content = message.text.replace("/broadcast", "").strip()
    if not content:
        return await message.reply("❗ Dùng: /broadcast <nội dung>")

    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    success, fail = 0, 0
    
    for uid in activated_users.keys():
        try:
            await bot.send_message(int(uid), f"📢 THÔNG BÁO:\n\n{content}\n\n⏰ Time: {now_str}")
            success += 1
            await asyncio.sleep(0.05)  # Tránh rate limit
        except Exception as e:
            print(f"Gửi tin nhắn thất bại cho {uid}: {e}")
            fail += 1
    
    await message.reply(f"✅ Gửi thành công: {success}\n❌ Thất bại: {fail}\n\n⏰ Thời gian: {now_str}")

# === ADMIN: DANH SÁCH USER ===
@dp.message_handler(commands=["danhsach"])
async def danhsach_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.reply("⛔ Bạn không có quyền.")
    
    if not activated_users:
        await message.reply("📋 Danh sách người dùng trống.")
        return
    
    lines = ["📋 DANH SÁCH NGƯỜI DÙNG ĐÃ KÍCH HOẠT:"]
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    for uid, info in activated_users.items():
        if uid == str(ADMIN_ID):
            lines.append(f"👑 Admin ID: {uid}")
            lines.append(f"   📅 Hạn: Vĩnh viễn")
        else:
            lines.append(f"👤 ID: {uid}")
            lines.append(f"   📅 Hạn: {info['expires']}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Gửi từng phần nếu danh sách quá dài
    if len("\n".join(lines)) > 4000:
        await message.reply("📋 Danh sách quá dài, vui lòng kiểm tra file data.")
    else:
        await message.reply("\n".join(lines))

# === XỬ LÝ MD5 ===
@dp.message_handler(lambda msg: len(msg.text) == 32 and all(c in '0123456789abcdefABCDEF' for c in msg.text))
async def md5_handler(message: types.Message):
    ok, _ = check_user(message.from_user.id)
    if not ok:
        await message.reply("🚫 Bạn chưa được cấp quyền sử dụng bot này\n📞 Liên hệ admin để được cấp quyền!")
        return
    
    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    result = analyze_md5_advanced(message.text.lower())

    reply_text = (
        f"<b>Dự Đoán MD5 SHA5 🎮</b>\n\n"
        f"🔮 Md5: <code>{message.text.lower()}</code>\n"
        f"👾 <b>Dự Đoán: 🎮</b> {'TÀI' if result['tai'] >= 50 else 'XỈU'} 🌌
🤖\n"
        f"🔴Tài: <b>{result['tai']}%</b>\n"
        f"⚫️Xỉu: <b>{result['xiu']}%</b>\n\n"
        f"👤 <b>{message.from_user.full_name}</b>\n"
        f"🆔 <b>{message.from_user.id}</b>\n"
        f"⏰ {now_str}"
    )
    await message.reply(reply_text, parse_mode="HTML")

# === KHỞI ĐỘNG BOT ===
if __name__ == '__main__':
    print("🚀 Bot đang khởi động...")
    print(f"📁 Thư mục data: {DATA_DIR}")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📊 Số users: {len(activated_users)}")
    
    # Kiểm tra token
    if TOKEN == "8684463452:AAF63cKhatW3kk1ZLORZEfN6j7kzfGQjLiI":
        print("⚠️ CẢNH BÁO: Bạn đang dùng token mặc định, hãy đặt biến môi trường TOKEN!")
    
    keep_alive()  # Giữ bot chạy
    executor.start_polling(dp, skip_updates=True)