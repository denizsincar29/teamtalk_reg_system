"""TeamTalk .tt file generator and URL utilities."""

import urllib.parse
from xml.etree import ElementTree as ET

from .config import SERVER_CONFIG


def generate_tt_file(username: str, password: str) -> str:
    """Generate a TeamTalk .tt configuration file content.
    
    The .tt file is an XML file that contains server connection information
    and user credentials for the TeamTalk client.
    
    Args:
        username: The user's username.
        password: The user's password.
        
    Returns:
        XML content as a string.
    """
    # Create root element
    teamtalk = ET.Element("teamtalk")
    teamtalk.set("version", "5.0")
    
    # Create host element
    host = ET.SubElement(teamtalk, "host")
    
    # Server connection details
    name = ET.SubElement(host, "name")
    name.text = f"{SERVER_CONFIG['host']} - {username}"
    
    address = ET.SubElement(host, "address")
    address.text = SERVER_CONFIG["host"]
    
    tcpport = ET.SubElement(host, "tcpport")
    tcpport.text = str(SERVER_CONFIG["tcp_port"])
    
    udpport = ET.SubElement(host, "udpport")
    udpport.text = str(SERVER_CONFIG["udp_port"])
    
    encrypted = ET.SubElement(host, "encrypted")
    encrypted.text = "false"
    
    # Authentication
    auth = ET.SubElement(host, "auth")
    
    auth_username = ET.SubElement(auth, "username")
    auth_username.text = username
    
    auth_password = ET.SubElement(auth, "password")
    auth_password.text = password
    
    # Join settings (join root channel by default)
    join = ET.SubElement(host, "join")
    
    channel = ET.SubElement(join, "channel")
    channel.text = "/"
    
    channel_password = ET.SubElement(join, "password")
    channel_password.text = ""
    
    # Generate XML string with declaration
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content = ET.tostring(teamtalk, encoding="unicode")
    
    return xml_declaration + xml_content


def generate_tt_url(username: str, password: str) -> str:
    """Generate a tt:// URL for direct connection.
    
    The tt:// protocol URL format:
    tt://[username[:password]@]hostname[:tcpport[:udpport]][/channel[/subchannel][?password]]
    
    Args:
        username: The user's username.
        password: The user's password.
        
    Returns:
        A tt:// URL string.
    """
    host = SERVER_CONFIG["host"]
    tcp_port = SERVER_CONFIG["tcp_port"]
    udp_port = SERVER_CONFIG["udp_port"]
    
    # URL encode username and password
    encoded_username = urllib.parse.quote(username, safe="")
    encoded_password = urllib.parse.quote(password, safe="")
    
    # Build the tt:// URL
    # Format: tt://username:password@host:tcpport:udpport/
    url = f"tt://{encoded_username}:{encoded_password}@{host}:{tcp_port}:{udp_port}/"
    
    return url


def get_server_info() -> dict:
    """Get server connection information.
    
    Returns:
        Dictionary with server connection details.
    """
    return {
        "host": SERVER_CONFIG["host"],
        "tcp_port": SERVER_CONFIG["tcp_port"],
        "udp_port": SERVER_CONFIG["udp_port"],
    }
