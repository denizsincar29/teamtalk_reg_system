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
