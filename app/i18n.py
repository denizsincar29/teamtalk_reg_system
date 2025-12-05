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
        "channels_join_root": "Join Root",
        "channels_leave_root": "Leave Root",
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
        
        # Scheduler
        "scheduler_header": "Scheduler",
        "scheduler_add_task": "Add Task",
        "scheduler_task_name": "Task Name",
        "scheduler_task_type": "Task Type",
        "scheduler_broadcast": "Broadcast",
        "scheduler_channel_message": "Channel Message",
        "scheduler_pm_online": "PM (if online)",
        "scheduler_on_user_login": "On User Login",
        "scheduler_status_change": "Status Change",
        "scheduler_message": "Message",
        "scheduler_target_channel": "Target Channel",
        "scheduler_target_username": "Target Username",
        "scheduler_any_user": "(any user)",
        "scheduler_delay_seconds": "Delay (seconds)",
        "scheduler_delay_min": "Min Delay",
        "scheduler_delay_max": "Max Delay",
        "scheduler_scheduled_time": "Scheduled Time",
        "scheduler_recurring": "Recurring",
        "scheduler_every_minutes": "Every (minutes)",
        "scheduler_one_time": "One-time",
        "scheduler_event_triggered": "Event-triggered",
        "scheduler_enabled": "Enabled",
        "scheduler_disabled": "Disabled",
        "scheduler_run_now": "Run Now",
        "scheduler_edit": "Edit",
        "scheduler_delete": "Delete",
        "scheduler_save": "Save",
        "scheduler_cancel": "Cancel",
        "scheduler_no_tasks": "No scheduled tasks",
        "scheduler_task_created": "Task created successfully",
        "scheduler_task_updated": "Task updated successfully",
        "scheduler_task_deleted": "Task deleted successfully",
        "scheduler_task_executed": "Task executed successfully",
        "scheduler_error": "Scheduler error",
        "scheduler_status_mode": "Status Mode",
        "scheduler_status_online": "Online",
        "scheduler_status_away": "Away",
        "scheduler_status_question": "Question",
        
        # Bot status
        "bot_status_header": "Bot Status",
        "bot_status_mode": "Status Mode",
        "bot_status_message": "Status Message",
        "bot_status_save": "Save Status",
        "bot_status_success": "Status updated successfully",
        "bot_status_error": "Failed to update status",
        
        # User actions (kick/ban)
        "kick_user": "Kick",
        "ban_user": "Ban",
        "kick_user_success": "User kicked successfully",
        "kick_user_error": "Failed to kick user",
        "ban_user_success": "User banned successfully",
        "ban_user_error": "Failed to ban user",
        "confirm_kick": "Are you sure you want to kick this user?",
        "confirm_ban": "Are you sure you want to ban this user?",
        
        # Offline PM
        "pm_queued": "Message queued for delivery when user comes online",
        
        # Main tabs
        "tab_users": "Users",
        "tab_chat": "Chat",
        "tab_server": "Server",
        
        # Audio streaming
        "audio_header": "Audio Streaming",
        "audio_upload": "Upload WAV",
        "audio_upload_hint": "Select a WAV file (max 10 MB)",
        "audio_files": "Audio Files",
        "audio_no_files": "No audio files uploaded",
        "audio_play": "Play",
        "audio_stop": "Stop",
        "audio_delete": "Delete",
        "audio_upload_success": "File uploaded successfully",
        "audio_upload_error": "Failed to upload file",
        "audio_play_success": "Audio streaming started",
        "audio_play_error": "Failed to start streaming",
        "audio_stop_success": "Audio streaming stopped",
        "audio_stop_error": "Failed to stop streaming",
        "audio_delete_success": "File deleted",
        "audio_delete_error": "Failed to delete file",
        "audio_confirm_delete": "Are you sure you want to delete this file?",
        
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
        "channels_join_root": "Войти в корневой",
        "channels_leave_root": "Выйти из корневого",
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
        
        # Scheduler
        "scheduler_header": "Планировщик",
        "scheduler_add_task": "Добавить задачу",
        "scheduler_task_name": "Название задачи",
        "scheduler_task_type": "Тип задачи",
        "scheduler_broadcast": "Рассылка",
        "scheduler_channel_message": "Сообщение в канал",
        "scheduler_pm_online": "ЛС (если онлайн)",
        "scheduler_on_user_login": "При входе пользователя",
        "scheduler_status_change": "Изменение статуса",
        "scheduler_message": "Сообщение",
        "scheduler_target_channel": "Целевой канал",
        "scheduler_target_username": "Целевой пользователь",
        "scheduler_any_user": "(любой пользователь)",
        "scheduler_delay_seconds": "Задержка (секунд)",
        "scheduler_delay_min": "Мин. задержка",
        "scheduler_delay_max": "Макс. задержка",
        "scheduler_scheduled_time": "Запланированное время",
        "scheduler_recurring": "Повторяющаяся",
        "scheduler_every_minutes": "Каждые (минут)",
        "scheduler_one_time": "Одноразовая",
        "scheduler_event_triggered": "По событию",
        "scheduler_enabled": "Включена",
        "scheduler_disabled": "Отключена",
        "scheduler_run_now": "Выполнить сейчас",
        "scheduler_edit": "Редактировать",
        "scheduler_delete": "Удалить",
        "scheduler_save": "Сохранить",
        "scheduler_cancel": "Отмена",
        "scheduler_no_tasks": "Нет запланированных задач",
        "scheduler_task_created": "Задача успешно создана",
        "scheduler_task_updated": "Задача успешно обновлена",
        "scheduler_task_deleted": "Задача успешно удалена",
        "scheduler_task_executed": "Задача успешно выполнена",
        "scheduler_error": "Ошибка планировщика",
        "scheduler_status_mode": "Режим статуса",
        "scheduler_status_online": "Онлайн",
        "scheduler_status_away": "Отошёл",
        "scheduler_status_question": "Вопрос",
        
        # Bot status
        "bot_status_header": "Статус бота",
        "bot_status_mode": "Режим статуса",
        "bot_status_message": "Сообщение статуса",
        "bot_status_save": "Сохранить статус",
        "bot_status_success": "Статус успешно обновлён",
        "bot_status_error": "Не удалось обновить статус",
        
        # User actions (kick/ban)
        "kick_user": "Кикнуть",
        "ban_user": "Забанить",
        "kick_user_success": "Пользователь кикнут",
        "kick_user_error": "Не удалось кикнуть пользователя",
        "ban_user_success": "Пользователь забанен",
        "ban_user_error": "Не удалось забанить пользователя",
        "confirm_kick": "Вы уверены, что хотите кикнуть этого пользователя?",
        "confirm_ban": "Вы уверены, что хотите забанить этого пользователя?",
        
        # Offline PM
        "pm_queued": "Сообщение поставлено в очередь для доставки при входе пользователя",
        
        # Main tabs
        "tab_users": "Пользователи",
        "tab_chat": "Чат",
        "tab_server": "Сервер",
        
        # Audio streaming
        "audio_header": "Аудио трансляция",
        "audio_upload": "Загрузить WAV",
        "audio_upload_hint": "Выберите WAV файл (макс. 10 МБ)",
        "audio_files": "Аудио файлы",
        "audio_no_files": "Нет загруженных аудио файлов",
        "audio_play": "Воспроизвести",
        "audio_stop": "Остановить",
        "audio_delete": "Удалить",
        "audio_upload_success": "Файл успешно загружен",
        "audio_upload_error": "Не удалось загрузить файл",
        "audio_play_success": "Трансляция аудио запущена",
        "audio_play_error": "Не удалось запустить трансляцию",
        "audio_stop_success": "Трансляция аудио остановлена",
        "audio_stop_error": "Не удалось остановить трансляцию",
        "audio_delete_success": "Файл удалён",
        "audio_delete_error": "Не удалось удалить файл",
        "audio_confirm_delete": "Вы уверены, что хотите удалить этот файл?",
        
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
