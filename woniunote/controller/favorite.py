from flask import Blueprint, request, session
from woniunote.module.favorites import Favorites
import traceback

favorite = Blueprint('favorite', __name__)


@favorite.route('/favorite', methods=['POST'])
def add_favorite():
    try:
        articleid = request.form.get('articleid')
        if not session.get('main_islogin'):
            return 'not-login'
        
        if Favorites().insert_favorite(articleid):
            return 'favorite-pass'
        return 'favorite-fail'
    except Exception as e:
        print("Error in add_favorite:", e)
        traceback.print_exc()
        return 'favorite-fail'


@favorite.route('/favorite/<int:articleid>', methods=['DELETE'])
def cancel_favorite(articleid):
    try:
        if not session.get('main_islogin'):
            return 'not-login'
        
        if Favorites().cancel_favorite(articleid):
            return 'cancel-pass'
        return 'cancel-fail'
    except Exception as e:
        print("Error in cancel_favorite:", e)
        traceback.print_exc()
        return 'cancel-fail'
