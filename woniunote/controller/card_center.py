from flask import render_template, redirect, abort, jsonify, current_app
from woniunote.controller.user import *
from woniunote.common.database import db
from woniunote.models.card import Card, CardCategory
from functools import wraps
import datetime
import logging
import time

card_center = Blueprint("card_center", __name__)

# Setup logger for card_center
logger = logging.getLogger(__name__)

# Decorator for requiring login
def login_required(f):
    """Decorator to check if user is logged in before accessing card functions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('main_islogin') is None:
            logger.warning(f"Unauthorized access attempt to {f.__name__}")
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

# Decorator for database error handling
def db_error_handler(f):
    """Decorator to handle database errors consistently"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error in {f.__name__}: {str(e)}")
            # In a production app, we might want to return a more user-friendly error page
            return jsonify({"error": "An error occurred while processing your request"}), 500
    return decorated_function


def cal_leave_day(target_date):
    """Calculate the number of days that have passed since the target_date.
    
    Args:
        target_date (datetime): The reference date to calculate days from
        
    Returns:
        int: Number of days passed (non-negative). Returns 0 if target_date is None.
    """
    if not target_date:
        return 0
    now_datetime = datetime.datetime.now()
    total_delta = now_datetime - target_date
    days_passed = total_delta.days
    # Ensure we return a non-negative value
    return max(0, days_passed)


@card_center.route('/cards/', methods=['GET', 'POST'])
@login_required
def card_index():
    """Main entry point for the card management functionality.
    
    Returns:
        Response: Redirects to the default category view.
    """
    logger.debug("Accessed card index page")
    return redirect(f"/cards/category/1")


@card_center.route('/cards/add_new_card', methods=['GET', 'POST'])
@login_required
@db_error_handler
def add_new_card():
    """Add a new card to the system.
    
    POST parameters:
        card_headline: Title of the card
        card_date: Date for the card
        category: Category ID for the card
        card_type: Type of card
        
    Returns:
        Response: Redirects to the category page after creation
    """
    if request.method == 'POST':
        headline = request.form.get('card_headline')
        card_date = request.form.get('card_date')
        category_id = request.form.get('category')
        card_type = request.form.get('card_type')
        now_time = datetime.datetime.now()
        
        logger.info(f"Creating new card: {headline} in category {category_id}")
        
        card_category = CardCategory.query.get_or_404(category_id)
        card_item = Card(headline=headline,
                         createtime=now_time,
                         updatetime=card_date,
                         cardcategory=card_category,
                         usedtime=0,
                         type=card_type)
        db.session.add(card_item)
        db.session.commit()
        return redirect(f"/cards/category/{category_id}")
    
    return redirect(f"/cards/category/1")


@card_center.route('/cards/begin_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def begin_card(card_id):
    """Mark a card as started by setting its begin time.
    
    Args:
        card_id (int): ID of the card to start
        
    Returns:
        Response: Redirects to the category page after updating
    """
    logger.info(f"Starting card with ID: {card_id}")
    
    card = Card.query.get_or_404(card_id)
    category_id = card.cardcategory_id
    
    card.begintime = datetime.datetime.now()
    card.endtime = None
    
    db.session.add(card)
    db.session.commit()
    
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/end_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def end_card(card_id):
    """Mark a card as ended by setting its end time and calculating usage time.
    
    For cards with "重复" (repeat) in the title, this creates a completed version in the done category
    and keeps the original for future use.
    
    Args:
        card_id (int): ID of the card to end
        
    Returns:
        Response: Redirects to the category page after updating
    """
    logger.info(f"Ending card with ID: {card_id}")
    
    card = Card.query.get_or_404(card_id)
    head_line = card.headline
    category_id = card.cardcategory_id
    now_time = datetime.datetime.now()
    
    # Set end time
    card.endtime = now_time
    begin_datetime = card.begintime
    
    # Initialize usedtime if not set
    if not card.usedtime:
        card.usedtime = 0
    
    # Calculate time spent
    if not begin_datetime:
        total_seconds = 0
    else:
        total_seconds = (now_time - begin_datetime).seconds
        
    logger.debug(f"Card {card_id} used {total_seconds} seconds this session")
    
    # Update the used time
    used_time = total_seconds + card.usedtime
    card.usedtime = used_time
    card.begintime = None
    
    # Special handling for repeating cards
    if "重复" in head_line:
        logger.info(f"Processing repeating card: {head_line}")
        
        # Create completed version in the done category
        done_category = CardCategory.query.get_or_404(2) # Done category has ID 2
        new_head_line = head_line.replace("重复", "")
        
        done_card = Card(headline=new_head_line, 
                         cardcategory=done_category,
                         begintime=None,
                         endtime=now_time,
                         donetime=now_time,
                         usedtime=(now_time - begin_datetime).seconds if begin_datetime else 0)
        
        db.session.add(done_card)
        db.session.add(card)
        db.session.commit()
    else:
        # Normal card ending
        db.session.add(card)
        db.session.commit()
    
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/category/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def category(card_id):
    """Display card category view with filtering based on category type.
    
    This function handles the main card viewing interface, applying
    different filters based on the category type (time-based, priority-based).
    
    Args:
        card_id (int): ID of the category to display
        
    Returns:
        Response: Renders the card_index.html template with filtered cards
    """
    logger.info(f"Accessing category view for ID: {card_id}")
    
    # Handle done category specially
    if card_id == 2:  # ID 2 is the 'Done' category
        logger.debug("Accessing done category, redirecting to get_done_category")
        return _handle_done_category()
    
    # Get all categories
    categories = CardCategory.query.all()
    if not categories:
        logger.error("Failed to retrieve card categories")
        return jsonify({"error": "Unable to load categories"}), 500
    
    # Get the current category
    card_category = CardCategory.query.get_or_404(card_id)
    category_name = card_category.name
    
    # Process all cards and create filtered collections
    card_collections = _prepare_card_collections(categories)
    
    # Select the appropriate items based on category
    items = _select_items_for_category(card_category, card_collections, card_id)
    
    # Ensure all dictionaries have safe default values
    times_cards = card_collections['times_cards']
    types_cards = card_collections['types_cards']
    _ensure_safe_defaults(categories, times_cards, types_cards)
    
    # Render the template with all necessary data
    return render_template('card_index.html', 
                          items=items,
                          categories=categories,
                          category_now=card_category,
                          types_cards=types_cards,
                          times_cards=times_cards,
                          all_begin_cards=card_collections['all_begin_cards'],
                          important_cards=card_collections['important_cards'])


def _handle_done_category():
    """Handle the 'Done' category view (card_id = 2).
    
    Groups completed cards by month and redirects to the view
    for the most recent month.
    
    Returns:
        Response: Redirects to the appropriate month view
    """
    # Get the done category
    done_category = CardCategory.query.get_or_404(2)
    done_items = done_category.cards
    
    # Group cards by month
    month_cards = {}
    for card in done_items:
        if not card.donetime:
            continue
            
        try:
            item_done_time = int(str(card.donetime)[:4] + str(card.donetime)[5:7])
            if item_done_time not in month_cards:
                month_cards[item_done_time] = []
            month_cards[item_done_time].append(card)
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"Error processing donetime for card {card.id}: {e}")
    
    # If no cards with donetime, return empty page
    if not month_cards:
        logger.info("No completed cards found")
        return render_template('card_index.html', 
                              items=[],
                              categories=CardCategory.query.all(),
                              category_now=done_category,
                              types_cards={},
                              times_cards={},
                              all_begin_cards=[],
                              important_cards=[])
    
    # Get the most recent month
    month_list = sorted(list(month_cards.keys()), reverse=True)
    return get_done_category(month_list[0])


def _prepare_card_collections(categories):
    """Prepare various card collections for filtering.
    
    Categorizes cards by type, time periods, and started status.
    
    Args:
        categories (list): List of all CardCategory objects
        
    Returns:
        dict: Dictionary containing various card collections
    """
    # Collect all cards
    all_cards = []
    for category in categories:
        all_cards.extend(category.cards)
    
    # Filter and sort undone cards
    all_undone_cards = [card for card in all_cards if not card.donetime]
    all_undone_cards = sorted(all_undone_cards, key=lambda x: getattr(x, "updatetime"))
    
    # Filter cards that have been started
    all_begin_cards = [card for card in all_cards if card.begintime]
    
    # Group cards by priority type
    type_1_cards = [card for card in all_undone_cards if card.type == 1]
    type_2_cards = [card for card in all_undone_cards if card.type == 2]
    type_3_cards = [card for card in all_undone_cards if card.type == 3]
    type_4_cards = [card for card in all_undone_cards if card.type == 4]
    
    # Create a dictionary for priority-based categories
    types_cards = {
        "重要紧急": type_1_cards, 
        "重要不紧急": type_2_cards,
        "紧急不重要": type_3_cards, 
        "不重要不紧急": type_4_cards,
        "已开始清单": all_begin_cards
    }
    
    # Create time-based categories
    time_categories = _categorize_cards_by_time(all_undone_cards)
    
    # Combine important cards
    important_cards = type_1_cards + type_2_cards
    
    return {
        'all_undone_cards': all_undone_cards,
        'all_begin_cards': all_begin_cards,
        'types_cards': types_cards,
        'times_cards': time_categories,
        'important_cards': important_cards
    }


def _categorize_cards_by_time(all_undone_cards):
    """Categorize cards by time periods based on updatetime.
    
    Args:
        all_undone_cards (list): List of cards that are not completed
        
    Returns:
        dict: Dictionary mapping time category names to card lists
    """
    day_cards = []
    week_cards = []
    month_cards = []
    year_cards = []
    ten_year_cards = []
    
    for card in all_undone_cards:
        leave_day = cal_leave_day(card.updatetime)
        
        if leave_day <= 1:
            day_cards.append(card)
        elif 1 < leave_day <= 7:
            week_cards.append(card)
        elif 7 < leave_day <= 30:
            month_cards.append(card)
        elif 30 < leave_day <= 365:
            year_cards.append(card)
        else:  # leave_day > 365
            ten_year_cards.append(card)
    
    return {
        "日清单": day_cards, 
        "周清单": week_cards,
        "月清单": month_cards, 
        "年清单": year_cards, 
        "十年清单": ten_year_cards
    }


def _select_items_for_category(card_category, card_collections, card_id):
    """Select the appropriate items for the given category.
    
    Args:
        card_category (CardCategory): The current category object
        card_collections (dict): Dictionary of card collections
        card_id (int): ID of the current category
        
    Returns:
        list: The filtered list of cards to display
    """
    category_name = card_category.name
    
    # Start with the cards directly in this category
    items = card_category.cards
    items = sorted(items, key=lambda x: getattr(x, "updatetime"))
    
    # Apply special filtering based on category name
    time_categories = ["日清单", "周清单", "月清单", "年清单", "十年清单"]
    priority_categories = ["不重要不紧急", "紧急不重要", "重要不紧急", "重要紧急"]
    
    # Handle time-based categories
    if category_name in time_categories:
        items = card_collections['times_cards'].get(category_name, [])
        
    # Handle priority-based categories
    elif category_name in priority_categories:
        items = card_collections['types_cards'].get(category_name, [])
        
    # Handle special case for the default view (card_id = 1)
    elif card_id == 1 and len(card_collections['important_cards']) > 0:
        items = card_collections['important_cards']
        
    # Handle started cards list
    elif category_name == "已开始清单":
        items = card_collections['all_begin_cards']
        
    return items


def _ensure_safe_defaults(categories, times_cards, types_cards):
    """Ensure all dictionaries have safe default values to prevent KeyError.
    
    Args:
        categories (list): List of all CardCategory objects
        times_cards (dict): Dictionary of time-based card collections
        types_cards (dict): Dictionary of priority-based card collections
    """
    time_categories = ["日清单", "周清单", "月清单", "年清单", "十年清单"]
    priority_categories = ["不重要不紧急", "紧急不重要", "重要不紧急", "重要紧急", "已开始清单"]
    
    for category in categories:
        # Ensure time categories exist
        if category.name in time_categories and category.name not in times_cards:
            times_cards[category.name] = []
            
        # Ensure priority categories exist
        if category.name in priority_categories and category.name not in types_cards:
            types_cards[category.name] = []


@card_center.route('/cards/category/2/<int:year_month>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def get_done_category(year_month):
    """Display done cards filtered by year and month.
    
    This view shows completed cards for a specific year_month (format: YYYYMM).
    It provides navigation between different months of completed cards.
    
    Args:
        year_month (int): Year and month as a combined integer (YYYYMM format)
        
    Returns:
        Response: Renders the card_done_index.html template with the filtered cards
    """
    logger.info(f"Viewing done cards for year-month: {year_month}")
    
    # Get all categories
    categories = CardCategory.query.all()
    if not categories:
        logger.error("Failed to retrieve card categories")
        return jsonify({"error": "Unable to load categories"}), 500
    
    # Process all cards and create filtered collections
    card_collections = _prepare_card_collections(categories)
    
    # Get the done category (ID 2)
    done_category = CardCategory.query.get_or_404(2)
    done_items = done_category.cards
    
    # Group done cards by month
    month_cards_dict = _group_done_cards_by_month(done_items)
    
    # Handle missing year_month
    if year_month not in month_cards_dict:
        logger.warning(f"Requested year_month {year_month} not found in done cards")
        if not month_cards_dict:
            # No done cards at all
            return render_template('card_done_index.html',
                                 items=[],
                                 year_month=year_month,
                                 categories=categories,
                                 category_now=done_category,
                                 types_cards=card_collections['types_cards'],
                                 times_cards=card_collections['times_cards'],
                                 all_begin_cards=card_collections['all_begin_cards'],
                                 important_cards=card_collections['important_cards'],
                                 month_cards={},
                                 month_list=[])
        # Redirect to the most recent month instead
        month_list = sorted(list(month_cards_dict.keys()), reverse=True)
        logger.info(f"Redirecting to most recent month: {month_list[0]}")
        return redirect(f"/cards/category/2/{month_list[0]}")
    
    # Get cards for the selected month and sort in reverse order (newest first)
    filtered_items = month_cards_dict[year_month]
    filtered_items = sorted(filtered_items, key=lambda x: x.donetime, reverse=True)
    
    # Get sorted list of months for navigation
    month_list = sorted(list(month_cards_dict.keys()), reverse=True)
    
    # Render the template
    return render_template('card_done_index.html',
                          items=filtered_items,
                          year_month=year_month,
                          categories=categories,
                          category_now=done_category,
                          types_cards=card_collections['types_cards'],
                          times_cards=card_collections['times_cards'],
                          all_begin_cards=card_collections['all_begin_cards'],
                          important_cards=card_collections['important_cards'],
                          month_cards=month_cards_dict,
                          month_list=month_list)


def _group_done_cards_by_month(done_items):
    """Group done cards by month based on their done time.
    
    Args:
        done_items (list): List of completed cards
        
    Returns:
        dict: Dictionary mapping year_month (YYYYMM) to lists of cards
    """
    month_cards = {}
    
    for card in done_items:
        if not card.donetime:
            continue
            
        try:
            # Extract year and month as a combined integer (YYYYMM)
            item_done_time = int(str(card.donetime)[:4] + str(card.donetime)[5:7])
            
            if item_done_time not in month_cards:
                month_cards[item_done_time] = []
                
            month_cards[item_done_time].append(card)
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"Error processing donetime for card {card.id}: {e}")


@card_center.route('/cards/new_category', methods=['GET', 'POST'])
@login_required
@db_error_handler
def new_category():
    """Create a new card category.
    
    POST parameters:
        name: Name of the new category
        
    Returns:
        Response: Redirects to the new category page after creation
    """
    name = request.form.get('name')
    
    if not name or name.strip() == "":
        logger.warning("Attempted to create category with empty name")
        return jsonify({"error": "Category name cannot be empty"}), 400
        
    logger.info(f"Creating new category: {name}")
    
    card_category = CardCategory(name=name)
    db.session.add(card_category)
    db.session.commit()
    
    return redirect(f"/cards/category/{card_category.id}")


@card_center.route('/cards/edit_card/<int:card_id>', methods=['GET', 'POST'])
def edit_card(card_id):
    if session.get('main_islogin') is None:
        abort(404)

    card_0 = Card.query.get_or_404(card_id)
    # print(id,card.id,card.headline)
    categories = CardCategory.query.all()
    all_cards = []
    for card_category in categories:
        now_cards = card_category.cards
        all_cards.extend(now_cards)
    all_undone_cards = [card for card in all_cards if not card.donetime]
    type_1_cards = [i for i in all_undone_cards if i.type == 1]
    type_2_cards = [i for i in all_undone_cards if i.type == 2]
    type_3_cards = [i for i in all_undone_cards if i.type == 3]
    type_4_cards = [i for i in all_undone_cards if i.type == 4]
    # ["不重要不紧急","紧急不重要","重要不紧急","重要紧急"]
    types_cards = {"重要紧急": type_1_cards, "重要不紧急": type_2_cards,
                   "紧急不重要": type_3_cards, "不重要不紧急": type_4_cards}
    day_cards = []
    week_cards = []
    month_cards = []
    year_cards = []
    ten_year_cards = []
    for card in all_undone_cards:
        leave_day = cal_leave_day(card.updatetime)
        # print(card,card.headline,card.updatetime,leave_day)
        if leave_day <= 1:
            day_cards.append(card)
        if 1 < leave_day <= 7:
            week_cards.append(card)
        if 7 < leave_day <= 30:
            month_cards.append(card)
        if 30 < leave_day <= 365:
            year_cards.append(card)
        if leave_day > 365:
            ten_year_cards.append(card)
    times_cards = {"日清单": day_cards, "周清单": week_cards,
                   "月清单": month_cards, "年清单": year_cards, "十年清单": ten_year_cards}

    card_category = card_0.cardcategory
    items = card_category.cards
    category_name = card_category.name
    if category_name in ["日清单", "周清单", "月清单", "年清单", "十年清单"]:
        # print("true,ri day")
        items = times_cards[category_name]
    if category_name in ["不重要不紧急", "紧急不重要", "重要不紧急", "重要紧急"]:
        items = types_cards[category_name]
    important_cards = type_1_cards + type_2_cards

    if card_id == 1:
        if len(type_1_cards) + len(type_2_cards) > 0:
            items = important_cards
    # print("calling edit card",id, card_0.id, card_0.headline, category_name)
    html_file = 'card_edit.html'
    return render_template(html_file, card=card_0,
                           items=items,
                           categories=categories,
                           category_now=card_category,
                           types_cards=types_cards,
                           times_cards=times_cards,
                           important_cards=important_cards, )


@card_center.route('/cards/edit_item/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def edit_item(card_id):
    """Edit an existing card's properties.
    
    Updates card attributes from form data, skipping any fields with value "None".
    
    Args:
        card_id (int): ID of the card to be edited
        
    POST parameters:
        category_id: ID of the category to assign the card to
        headline: Card title
        createtime: Creation timestamp
        updatetime: Update timestamp
        donetime: Completion timestamp
        begintime: Start timestamp
        endtime: End timestamp
        usedtime: Time used on the card in seconds
        card_type: Type of card
        content: Card content/description
        
    Returns:
        Response: Redirects to the category page after updating
    """
    logger.info(f"Editing card with ID: {card_id}")
    
    # Get the card or 404 if not found
    card = Card.query.get_or_404(card_id)
    
    # Get form data
    form_data = {
        'category_id': request.form.get('category_id'),
        'headline': request.form.get('headline'),
        'createtime': request.form.get('createtime'),
        'updatetime': request.form.get('updatetime'),
        'donetime': request.form.get('donetime'),
        'begintime': request.form.get('begintime'),
        'endtime': request.form.get('endtime'),
        'usedtime': request.form.get('usedtime'),
        'card_type': request.form.get('card_type'),
        'content': request.form.get('content')
    }
    
    # Update card fields where form value is not "None"
    if form_data['headline'] != "None":
        card.headline = form_data['headline']
        
    if form_data['createtime'] != "None":
        try:
            card.createtime = form_data['createtime']
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid createtime format: {form_data['createtime']}")
            
    if form_data['updatetime'] != "None":
        try:
            card.updatetime = form_data['updatetime']
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid updatetime format: {form_data['updatetime']}")
    
    # Handle timestamp fields that could be None
    if form_data['donetime'] != "None":
        try:
            card.donetime = form_data['donetime']
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid donetime format: {form_data['donetime']}")
    else:
        card.donetime = None

    if form_data['begintime'] != "None":
        try:
            card.begintime = form_data['begintime']
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid begintime format: {form_data['begintime']}")
    else:
        card.begintime = None

    if form_data['endtime'] != "None":
        try:
            card.endtime = form_data['endtime']
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid endtime format: {form_data['endtime']}")
    else:
        card.endtime = None

    # Handle other fields
    if form_data['card_type'] != "None":
        card.type = form_data['card_type']

    if form_data['usedtime'] != "None":
        try:
            card.usedtime = int(form_data['usedtime'])
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid usedtime value: {form_data['usedtime']}")

    if form_data['content'] != "None":
        card.content = form_data['content']

    if form_data['category_id'] != "None":
        try:
            category_id = int(form_data['category_id'])
            # Verify category exists
            CardCategory.query.get_or_404(category_id)
            card.cardcategory_id = category_id
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid category ID: {form_data['category_id']}")
            category_id = card.cardcategory_id
    else:
        category_id = card.cardcategory_id

    # Save changes
    db.session.add(card)
    db.session.commit()
    
    logger.info(f"Successfully updated card: {card.id}")
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/edit_category/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def edit_category(card_id):
    """Edit a card category name.
    
    Args:
        card_id (int): ID of the category to edit
        
    POST parameters:
        name: New name for the category
        
    Returns:
        Response: Redirects to the default category page after update
    """
    logger.info(f"Editing category with ID: {card_id}")
    
    card_category = CardCategory.query.get_or_404(card_id)
    name = request.form.get('name')
    
    if not name or name.strip() == "":
        logger.warning(f"Attempted to update category {card_id} with empty name")
        return jsonify({"error": "Category name cannot be empty"}), 400
    
    card_category.name = name
    db.session.add(card_category)
    db.session.commit()
    
    logger.info(f"Successfully updated category: {card_id}")
    return redirect(f"/cards/category/1")


@card_center.route('/cards/done/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def done(card_id):
    """Mark a card as done by moving it to the 'Done' category (ID 2).
    
    This creates a new card in the 'Done' category with the same properties
    and deletes the original card.
    
    Args:
        card_id (int): ID of the card to mark as done
        
    Returns:
        Response: Redirects to the original category page after completion
    """
    logger.info(f"Marking card {card_id} as done")
    
    # Get the original card
    card = Card.query.get_or_404(card_id)
    category_id = card.cardcategory_id
    
    # Create a timestamp for the completion
    now_time = datetime.datetime.now()
    
    # Get the 'Done' category (ID 2)
    done_category = CardCategory.query.get_or_404(2)
    
    # Create a new card in the 'Done' category
    done_card = Card(headline=card.headline, 
                     cardcategory=done_category,
                     begintime=card.begintime,
                     endtime=card.endtime,
                     donetime=now_time,
                     usedtime=card.usedtime,
                     content=card.content,
                     type=card.type)
    
    logger.debug(f"Moving card '{card.headline}' to Done category")
    
    # Add the new card and delete the original in a single transaction
    db.session.add(done_card)
    db.session.delete(card)
    db.session.commit()
    
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/delete_item/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def delete_item(card_id):
    """Delete a card item permanently.
    
    Args:
        card_id (int): ID of the card to delete
        
    Returns:
        Response: Redirects to the default category page after deletion
    """
    logger.info(f"Deleting card with ID: {card_id}")
    
    # Get the card or 404 if not found
    item = Card.query.get_or_404(card_id)
    category_id = item.cardcategory_id
    
    # Note: this check is redundant after get_or_404, but keeping for safety
    if item is None:
        logger.warning(f"Attempted to delete non-existent card: {card_id}")
        return redirect(f"/cards/category/1")
    
    # Delete the card
    db.session.delete(item)
    db.session.commit()
    
    logger.info(f"Successfully deleted card: {card_id}")
    return redirect(f"/cards/category/{category_id}")


@card_center.route('/cards/delete_category/<int:card_id>', methods=['GET', 'POST'])
@login_required
@db_error_handler
def delete_category(card_id):
    """Delete a card category if it's not a protected category (ID 1 or 2).
    
    Args:
        card_id (int): ID of the category to delete
        
    Returns:
        Response: Redirects to the default category page after deletion
    """
    logger.info(f"Attempting to delete category with ID: {card_id}")
    
    # Check if it's a protected category
    if card_id in [1, 2]:
        logger.warning(f"Attempted to delete protected category {card_id}")
        return redirect(f"/cards/category/1")
    
    card_category = CardCategory.query.get_or_404(card_id)
    
    # Check again if category exists (should never hit this due to get_or_404)
    if card_category is None:
        return redirect(f"/cards/category/1")
        
    db.session.delete(card_category)
    db.session.commit()
    
    # Always redirect to the default category after deletion
    return redirect(f"/cards/category/1")


if __name__ == "__main__":
    pass
