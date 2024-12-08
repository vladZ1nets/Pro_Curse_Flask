from datetime import datetime
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, session
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import re
from database import init_db, db_session
import models
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import celery_tasks
app = Flask(__name__)
app.secret_key = 'hbiuvgtgiujhn'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


#db = SQLAlchemy(app)
#migrate = Migrate(app, db)

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return func(*args, **kwargs)
    return wrapper


@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        error_text = request.args.get('error')
        return render_template('login.html', error_text=error_text)
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        init_db()
        user_data = db_session.execute(select(models.User).filter_by(login=username, password=password)).scalar()
        if user_data:
            session['logged_in'] = user_data.login
            session['user_id'] = user_data.id
            return redirect('/profile')
        else:
            return redirect('/login?error=not_valide')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':
        form_data = dict(request.form)
        init_db()
        user = models.User(**form_data)
        db_session.add(user)
        db_session.commit()
        return redirect('/login')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    return redirect('/login')


@app.route('/items', methods=['GET', 'POST'])
@login_required
def items():
    if request.method == 'GET':
        items = db_session.query(models.Item, models.Contract).\
            outerjoin(models.Contract,
                      (models.Item.id == models.Contract.item_id) &
                      (func.date(datetime.today()) >= func.date(models.Contract.start_date)) &
                      (func.date(datetime.today()) <= func.date(models.Contract.end_date))).all()

        render_items = []
        for item, contract in items:
            render_items.append({
                'name': item.name,
                'available': True if contract is None else False,
                'id': item.id,
                'description': item.description
            })

        return render_template('item.html', items=render_items)

    elif request.method == 'POST':
        if session.get('logged_in') is None:
            return redirect('/login')
        else:
            init_db()
            current_user = db_session.execute(select(models.User).where(models.User.login == session['logged_in'])).scalar()

            new_item = models.Item(**request.form)
            new_item.owner = current_user.id
            db_session.add(new_item)
            db_session.commit()

            return redirect('/items')


@app.route('/items/<item_id>', methods=['GET'])
@login_required
def item_detail(item_id):
    item = db_session.execute(select(models.Item).filter_by(id=item_id)).scalar()
    item_owner = db_session.execute(select(models.User).where(models.User.id == item.owner_id)).first()
    return render_template('item_detail.html',
                           item_id=item_id,
                           photo=item.photo,
                           name=item.name,
                           description=item.description,
                           phour=item.price_hour,
                           pday=item.price_day,
                           pweek=item.price_week,
                           pmonth=item.price_month,
                           owner=item_owner,
                           current_user=session.get('user_id'))

@app.route('/items/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    item = db_session.execute(select(models.Item).filter_by(id=item_id)).scalar()
    if item:
        if item.owner_id == session['user_id']:
            db_session.delete(item)
            db_session.commit()
            return redirect('/items')
        else:
            return 'You are not the owner of this item and cannot delete it', 403
    return 'Item not found', 404



@app.route('/items/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    item = db_session.execute(select(models.Item).filter_by(id=item_id)).scalar()
    if item:
        db_session.delete(item)
        db_session.commit()
        return redirect('/items')
    return 'Item not found', 404


@app.route('/profile', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@app.route('/me', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@login_required
def profile():
    if request.method == 'GET':
        user = db_session.execute(select(models.User).filter_by(id=session['user_id'])).scalar()
        return render_template('user.html', fullname=user.full_name)
    elif request.method == 'PUT':
        user = db_session.execute(select(models.User).filter_by(id=session['user_id'])).scalar()
        user.full_name = request.form.get('full_name')
        db_session.commit()
        return redirect('/profile')
    elif request.method == 'DELETE':
        user = db_session.execute(select(models.User).filter_by(id=session['user_id'])).scalar()
        db_session.delete(user)
        db_session.commit()
        session.pop('user_id', None)
        session.pop('logged_in', None)
        return redirect('/login')


@app.route('/profile/favorites', methods=['GET', 'POST', 'DELETE', 'PATCH'])
@login_required
def favorites():
    user_id = session['user_id']
    if request.method == 'GET':
        favorites = db_session.execute(select(models.Favorite).filter_by(user_id=user_id)).scalars().all()
        return render_template('favorites.html', favorites=favorites)
    elif request.method == 'POST':
        new_favorite = models.Favorite(user_id=user_id, item_id=request.form['item_id'])
        db_session.add(new_favorite)
        db_session.commit()
        return redirect('/profile/favorites')
    elif request.method == 'DELETE':
        favorite = db_session.execute(select(models.Favorite).filter_by(user_id=user_id, item_id=request.form['item_id'])).scalar()
        if favorite:
            db_session.delete(favorite)
            db_session.commit()
        return redirect('/profile/favorites')


@app.route('/profile/favorites/<int:favourite_id>', methods=['DELETE'])
def favorite_detail(favourite_id):
    favorite = db_session.execute(select(models.Favorite).filter_by(id=favourite_id)).scalar()
    if favorite:
        db_session.delete(favorite)
        db_session.commit()
        return redirect('/profile/favorites')
    return 'Favorite not found', 404


@app.route('/profile/search_history', methods=['GET', 'POST'])
@login_required
def search_history():
    user_id = session['user_id']

    if request.method == 'GET':
        history = db_session.execute(select(models.SearchHistory).filter_by(user_id=user_id)).scalars().all()
        return render_template('search_history.html', history=history)

    elif request.method == 'POST':
        action = request.form.get('action')

        if action == 'delete':
            search_id = request.form.get('search_id')
            db_session.execute(delete(models.SearchHistory).filter_by(id=search_id))
            db_session.commit()

        elif action == 'clear':
            db_session.execute(delete(models.SearchHistory).filter_by(user_id=user_id))
            db_session.commit()

        return redirect(url_for('search_history'))


@app.route('/leasers', methods=['GET'])
@login_required
def leasers():
    leasers = db_session.execute(select(models.User).filter(models.User.role == 'leaser')).scalars().all()
    return render_template('leasers.html', leasers=leasers)


@app.route('/leasers/<int:leaser_id>', methods=['GET'])
@login_required
def leaser_detail(leaser_id):
    leaser = db_session.execute(select(models.User).filter_by(id=leaser_id)).scalar()
    items = db_session.execute(select(models.Item).filter_by(owner_id=leaser.id)).scalars().all()
    contracts = db_session.execute(select(models.Contract).filter(
        (models.Contract.leaser_id == leaser.id) | (models.Contract.taker_id == leaser.id))).scalars().all()

    leaser.name = re.sub(r'([a-z])([A-Z])', r'\1 \2', leaser.name)
    leaser.contacts = re.sub(r'([a-z])([A-Z])', r'\1 \2', leaser.contacts)
    leaser.email = re.sub(r'([a-z])([A-Z])', r'\1 \2', leaser.email)


    return render_template('leaser_detail.html', leaser=leaser, items=items, contracts=contracts)


@app.route('/contracts', methods=['GET', 'POST'])
@login_required
def contracts():
    if request.method == 'GET':
        my_contracts = db_session.execute(select(models.Contract).filter_by(taker_id=session['user_id'])).scalars().all()
        contracts_by_my_Items = db_session.execute(select(models.Contract).filter_by(leaser_id=session['user_id'])).scalars().all()
        return render_template('contracts.html', my_contracts=my_contracts, contracts_by_my_Items=contracts_by_my_Items)
    elif request.method == 'POST':
        contract_data = request.form.to_dict()
        new_contract = models.Contract(**contract_data)
        taker_id = session['user_id']
        leased_item = db_session.execute(select(models.Item).filter_by(id=contract_data['item_id'])).scalar()
        new_contract.taker_id = taker_id
        new_contract.leaser_id = leased_item.owner_id
        db_session.add(new_contract)
        db_session.commit()
        #celery_tasks.send_email(new_contract.id)
        return redirect('/contracts')


@app.route('/contracts/<int:contract_id>', methods=['GET', 'PATCH', 'PUT'])
@login_required
def contract_detail(contract_id):
    contract = db_session.execute(select(models.Contract).filter_by(id=contract_id)).scalar()
    return render_template('contract_detail.html', contract=contract)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'GET':
        return render_template('search.html')
    elif request.method == 'POST':
        search_query = request.form['query']
        results = db_session.execute(select(models.Item).filter(models.Item.name.ilike(f'%{search_query}%'))).scalars().all()
        return render_template('search_results.html', results=results)


@app.route('/compare', methods=['GET'])
@login_required
def compare():
    if request.method == 'GET':
        contract_ids = request.args.getlist('contract_ids')

        if len(contract_ids) != 2:
            return "Please provide exactly two contract IDs in the 'contract_ids' parameter", 400

        contract_1 = db_session.execute(select(models.Contract).filter_by(id=contract_ids[0])).scalar()
        contract_2 = db_session.execute(select(models.Contract).filter_by(id=contract_ids[1])).scalar()

        if not contract_1 or not contract_2:
            return "One or both contracts not found.", 404

        return render_template('compare.html', contract_1=contract_1, contract_2=contract_2)

@app.route('/add_task', methods=['GET'])
def set_task():
    celery_tasks.add.delay(1,2)
    return "Task sent"

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)

