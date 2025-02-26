from flask import session, request

def get_current_session_id():
    """Get the current user's session ID from cookie"""
    return request.cookies.get('session_id')

def get_session_value(key):
    """Get a session value for the current user
    
    Args:
        key: The base key name (e.g. 'userid', 'username', etc.)
    Returns:
        The session value if found, None otherwise
    """
    session_id = get_current_session_id()
    if not session_id:
        return None
    return session.get(f'{key}_{session_id}')

def is_logged_in():
    """Check if the current user is logged in"""
    return get_session_value('islogin') == 'true'

def get_current_user_id():
    """Get the current user's ID"""
    return get_session_value('userid')

def get_current_username():
    """Get the current username"""
    return get_session_value('username')

def get_current_nickname():
    """Get the current user's nickname"""
    return get_session_value('nickname')

def get_current_role():
    """Get the current user's role"""
    return get_session_value('role')
