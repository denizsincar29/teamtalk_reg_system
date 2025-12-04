"""Internationalization (i18n) translations for the application."""

# Available languages
LANGUAGES = ["en", "ru"]
DEFAULT_LANGUAGE = "ru"

# Translation strings
TRANSLATIONS = {
    "en": {
        # Page titles
        "page_title": "TeamTalk Registration",
        "success_title": "Registration Successful - TeamTalk",
        
        # Registration form
        "registration_header": "TeamTalk Registration",
        "username_label": "Username:",
        "password_label": "Password:",
        "username_placeholder": "Enter your username",
        "password_placeholder": "Enter your password",
        "register_button": "Register",
        
        # Success page
        "success_header": "Registration Successful!",
        "success_message": 'User "<strong>{username}</strong>" has been registered successfully!',
        "connect_header": "Connect to TeamTalk Server",
        
        # Download options
        "option1_title": "Option 1: Download .tt File",
        "option1_desc": "Download a configuration file to open with TeamTalk client:",
        "download_button": "Download {username}.tt",
        "option2_title": "Option 2: Quick Connect",
        "option2_desc": "Click the link below to connect directly (requires TeamTalk installed):",
        "connect_button": "Connect via tt:// URL",
        "option3_title": "Server Details",
        "host_label": "Host:",
        "tcp_port_label": "TCP Port:",
        "udp_port_label": "UDP Port:",
        "username_detail_label": "Username:",
        
        # Navigation
        "back_link": "← Register another user",
        
        # Error messages
        "error_required": "Username and password are required.",
        "error_username_short": "Username must be at least {min_length} characters.",
        "error_password_short": "Password must be at least {min_length} characters.",
        "error_checking_user": "Error checking user: {error}",
        "error_user_exists": "Username already exists. Please choose another.",
        "error_create_failed": "Failed to create user: {error}",
        
        # Language switcher
        "language": "Language",
        "english": "English",
        "russian": "Русский",
        
        # Admin panel
        "admin_title": "Admin Panel - TeamTalk",
        "admin_header": "Admin Panel",
        "admin_login_header": "Admin Login",
        "admin_login_button": "Login",
        "admin_logout_button": "Logout",
        "admin_login_error": "Invalid credentials or not an admin account.",
        "admin_connecting": "Connecting to server...",
        "admin_connection_error": "Could not connect to the server.",
        
        # Admin panel tabs
        "tab_accounts": "User Accounts",
        "tab_online": "Online Users",
        "tab_messages": "Messages",
        
        # User accounts
        "accounts_header": "User Accounts",
        "accounts_loading": "Loading accounts...",
        "accounts_username": "Username",
        "accounts_type": "Type",
        "accounts_note": "Note",
        "accounts_type_default": "User",
        "accounts_type_admin": "Admin",
        "accounts_empty": "No user accounts found.",
        
        # Online users
        "online_header": "Online Users",
        "online_loading": "Loading users...",
        "online_username": "Username",
        "online_nickname": "Nickname",
        "online_channel": "Channel",
        "online_status": "Status",
        "online_send_message": "Send Message",
        "online_empty": "No users online.",
        
        # Private messages
        "pm_header": "Send Private Message",
        "pm_to_user": "To:",
        "pm_message": "Message:",
        "pm_send_button": "Send",
        "pm_sent_success": "Message sent successfully!",
        "pm_sent_error": "Failed to send message.",
        
        # Channel messages
        "messages_header": "Chat",
        "messages_from": "From",
        "messages_channel": "Channel",
        "messages_content": "Message",
        "messages_time": "Time",
        "messages_empty": "No messages yet. Start the conversation!",
        "messages_clear": "Clear Chat",
        "messages_reply": "Reply to Channel",
        "messages_reply_placeholder": "Type a message... (@user for private, @all for broadcast)",
        "messages_reply_send": "Send",
        "messages_reply_success": "Message sent!",
        "messages_reply_error": "Failed to send message.",
        "messages_private": "Private",
        "messages_broadcast": "Broadcast",
        "messages_sent_as_broadcast": "Message sent! (broadcast)",
        "messages_enable_sound": "🔔 Click to enable notification sounds",
        "messages_sound_enabled": "Notification sounds enabled",
        
        # Channels
        "channels_header": "Channels",
        "channels_join": "Join",
        "channels_leave": "Leave",
        "channels_current": "Current",
        "channels_has_password": "🔒",
        "channels_no_password": "",
        "channels_root": "Root",
        "channels_join_success": "Joined channel!",
        "channels_join_error": "Failed to join channel.",
        "channels_leave_success": "Left channel!",
        "channels_leave_error": "Failed to leave channel.",
        
        # Events
        "event_user_login": "{nickname} connected to server",
        "event_user_logout": "{nickname} disconnected from server",
        "event_user_join_channel": "{nickname} joined {channel}",
        "event_user_left_channel": "{nickname} left {channel}",
        "event_channel_new": "Channel {channel} created",
        "event_channel_delete": "Channel {channel} deleted",
        "event_bot_connected": "Bot connected to server",
        "event_connection_lost": "Connection to server lost",
        "event_root_channel": "root channel",
        "event_root_channel_genitive": "root channel",
        
        # Navigation
        "admin_back_to_registration": "← Back to Registration",
    },
    "ru": {
        # Page titles
        "page_title": "Регистрация TeamTalk",
        "success_title": "Регистрация успешна - TeamTalk",
        
        # Registration form
        "registration_header": "Регистрация TeamTalk",
        "username_label": "Имя пользователя:",
        "password_label": "Пароль:",
        "username_placeholder": "Введите имя пользователя",
        "password_placeholder": "Введите пароль",
        "register_button": "Зарегистрироваться",
        
        # Success page
        "success_header": "Регистрация успешна!",
        "success_message": 'Пользователь "<strong>{username}</strong>" успешно зарегистрирован!',
        "connect_header": "Подключение к серверу TeamTalk",
        
        # Download options
        "option1_title": "Вариант 1: Скачать .tt файл",
        "option1_desc": "Скачайте файл конфигурации для открытия в клиенте TeamTalk:",
        "download_button": "Скачать {username}.tt",
        "option2_title": "Вариант 2: Быстрое подключение",
        "option2_desc": "Нажмите на ссылку ниже для прямого подключения (требуется установленный TeamTalk):",
        "connect_button": "Подключиться через tt:// URL",
        "option3_title": "Данные сервера",
        "host_label": "Хост:",
        "tcp_port_label": "TCP Порт:",
        "udp_port_label": "UDP Порт:",
        "username_detail_label": "Имя пользователя:",
        
        # Navigation
        "back_link": "← Зарегистрировать другого пользователя",
        
        # Error messages
        "error_required": "Имя пользователя и пароль обязательны.",
        "error_username_short": "Имя пользователя должно быть не менее {min_length} символов.",
        "error_password_short": "Пароль должен быть не менее {min_length} символов.",
        "error_checking_user": "Ошибка проверки пользователя: {error}",
        "error_user_exists": "Имя пользователя уже существует. Выберите другое.",
        "error_create_failed": "Не удалось создать пользователя: {error}",
        
        # Language switcher
        "language": "Язык",
        "english": "English",
        "russian": "Русский",
        
        # Admin panel
        "admin_title": "Панель администратора - TeamTalk",
        "admin_header": "Панель администратора",
        "admin_login_header": "Вход администратора",
        "admin_login_button": "Войти",
        "admin_logout_button": "Выйти",
        "admin_login_error": "Неверные учётные данные или аккаунт не администратора.",
        "admin_connecting": "Подключение к серверу...",
        "admin_connection_error": "Не удалось подключиться к серверу.",
        
        # Admin panel tabs
        "tab_accounts": "Учётные записи",
        "tab_online": "Пользователи онлайн",
        "tab_messages": "Сообщения",
        
        # User accounts
        "accounts_header": "Учётные записи пользователей",
        "accounts_loading": "Загрузка учётных записей...",
        "accounts_username": "Имя пользователя",
        "accounts_type": "Тип",
        "accounts_note": "Примечание",
        "accounts_type_default": "Пользователь",
        "accounts_type_admin": "Администратор",
        "accounts_empty": "Учётные записи не найдены.",
        
        # Online users
        "online_header": "Пользователи онлайн",
        "online_loading": "Загрузка пользователей...",
        "online_username": "Имя пользователя",
        "online_nickname": "Псевдоним",
        "online_channel": "Канал",
        "online_status": "Статус",
        "online_send_message": "Отправить сообщение",
        "online_empty": "Нет пользователей онлайн.",
        
        # Private messages
        "pm_header": "Отправить личное сообщение",
        "pm_to_user": "Кому:",
        "pm_message": "Сообщение:",
        "pm_send_button": "Отправить",
        "pm_sent_success": "Сообщение отправлено!",
        "pm_sent_error": "Не удалось отправить сообщение.",
        
        # Channel messages
        "messages_header": "Чат",
        "messages_from": "От",
        "messages_channel": "Канал",
        "messages_content": "Сообщение",
        "messages_time": "Время",
        "messages_empty": "Пока нет сообщений. Начните разговор!",
        "messages_clear": "Очистить чат",
        "messages_reply": "Ответить в канал",
        "messages_reply_placeholder": "Введите сообщение... (@имя для личного, @all для рассылки)",
        "messages_reply_send": "Отправить",
        "messages_reply_success": "Сообщение отправлено!",
        "messages_reply_error": "Не удалось отправить сообщение.",
        "messages_private": "Личное",
        "messages_broadcast": "Рассылка",
        "messages_sent_as_broadcast": "Сообщение отправлено! (рассылка)",
        "messages_enable_sound": "🔔 Нажмите для включения звуковых уведомлений",
        "messages_sound_enabled": "Звуковые уведомления включены",
        
        # Channels
        "channels_header": "Каналы",
        "channels_join": "Войти",
        "channels_leave": "Выйти",
        "channels_current": "Текущий",
        "channels_has_password": "🔒",
        "channels_no_password": "",
        "channels_root": "Корневой",
        "channels_join_success": "Вошли в канал!",
        "channels_join_error": "Не удалось войти в канал.",
        "channels_leave_success": "Вышли из канала!",
        "channels_leave_error": "Не удалось выйти из канала.",
        
        # Events
        "event_user_login": "{nickname} подключился к серверу",
        "event_user_logout": "{nickname} отключился от сервера",
        "event_user_join_channel": "{nickname} вошёл в {channel}",
        "event_user_left_channel": "{nickname} вышел из {channel}",
        "event_channel_new": "Канал {channel} создан",
        "event_channel_delete": "Канал {channel} удалён",
        "event_bot_connected": "Бот подключён к серверу",
        "event_connection_lost": "Соединение с сервером потеряно",
        "event_root_channel": "корневой канал",
        "event_root_channel_genitive": "корневого канала",
        
        # Navigation
        "admin_back_to_registration": "← Вернуться к регистрации",
    }
}


def get_translation(lang: str, key: str, **kwargs) -> str:
    """Get a translation string for the given language and key.
    
    Args:
        lang: Language code (en, ru)
        key: Translation key
        **kwargs: Format arguments for the translation string
        
    Returns:
        Translated string, or the key if not found
    """
    if lang not in TRANSLATIONS:
        lang = DEFAULT_LANGUAGE
    
    text = TRANSLATIONS[lang].get(key, key)
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    
    return text


def get_translations(lang: str) -> dict:
    """Get all translations for a language.
    
    Args:
        lang: Language code (en, ru)
        
    Returns:
        Dictionary of all translations for the language
    """
    if lang not in TRANSLATIONS:
        lang = DEFAULT_LANGUAGE
    return TRANSLATIONS[lang]
