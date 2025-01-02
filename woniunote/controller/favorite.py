from flask import Blueprint, request, session

from woniunote.module.favorites import Favorites

favorite = Blueprint('favorite', __name__)


@favorite.route('/favorite', methods=['POST'])
def add_favorite():
    articleid = request.form.get('articleid')
    if session.get('islogin') is None:
        return 'not-login'
    else:
        try:
            Favorites().insert_favorite(articleid)
            return 'favorite-pass'
        except Exception as e:
            print("add favorite", e)
            return 'favorite-fail'


@favorite.route('/favorite/<int:articleid>', methods=['DELETE'])
def cancel_favorite(articleid):
    try:
        Favorites().cancel_favorite(articleid)
        return 'cancel-pass'
    except Exception as e:
        print("cancel favorite", e)
        return 'cancel-fail'
