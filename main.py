from flask import Flask, render_template, abort, request, redirect, url_for, flash, session
import os
import functools
from database import Database
from filters import register_filters
import hashlib

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.secret_key = '2262'  # Важно использовать надежный секретный ключ в продакшене

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def is_authenticated():
    """Проверяет, авторизован ли пользователь"""
    return session.get('authenticated', False)


def admin_required(f):
    """Декоратор для защиты админ-страниц"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Требуется авторизация для доступа к этой странице', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@app.route("/<name>/")
def render(name=None):
    db = Database()
    context = {}
    if name is None:
        try:
            posts = db.get_all_posts()
            context = {'page_name': 'Главная', 'posts': posts}
            return render_template("index.html", **context)
        except Exception as e:
            flash(f'Ошибка при загрузке постов: {str(e)}', 'error')
            return render_template("index.html", page_name='Главная', posts=[])
    elif name.lower() == 'contacts':
        context['page_name'] = 'Контакты'
        return render_template("contacts.html", **context)
    elif name.lower() == 'admin':
        return redirect(url_for('manage_posts'))
    else:
        abort(404)


# Новый маршрут для просмотра отдельного поста
@app.route('/post/<int:post_id>')
def view_post(post_id):
    db = Database()
    post = db.get_post(post_id)
    if not post:
        abort(404)
    return render_template('post.html', page_name=post['title'], post=post)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if is_authenticated():
        return redirect(url_for('manage_posts'))
    if request.method == 'POST':
        name = request.form.get('username')
        password = request.form.get('password')
        db = Database()
        if db.authenticate(name, password):
            session['authenticated'] = True
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('manage_posts'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    return render_template('admin_login.html', page_name='Вход в админ панель')


@app.route('/admin/logout')
def admin_logout():
    session.pop('authenticated', None)
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('render'))


@app.route('/admin/manage-posts/')
@admin_required
def manage_posts():
    db = Database()
    try:
        posts = db.get_all_posts()
        context = {'page_name': 'Управление постами', 'posts': posts}
        return render_template("manage_posts.html", **context)
    except Exception as e:
        flash(f'Ошибка при загрузке постов: {str(e)}', 'error')
        return redirect(url_for('render'))



@app.route('/admin/create-post/', methods=['GET', 'POST'])
@admin_required
def admin_create_post():
    if request.method == 'GET':
        return render_template("create_post.html", page_name='Создать пост')
    elif request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files['image']
        try:
            db = Database()
            max_id = db.get_max_post_id()
            post_id = max_id + 1
            relative_path = None
            if image and image.filename != '':
                ext = image.filename.split('.')[-1]
                filename = f"post_{post_id}.{ext}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                relative_path = os.path.join('uploads', filename).replace('\\', '/')
            db.insert_post(post_id=post_id, title=title, content=content, image=relative_path)
            flash('Пост успешно создан!', 'success')
        except Exception as e:
            flash(f'Ошибка при создании поста: {str(e)}', 'error')
        return redirect(url_for('manage_posts'))


@app.route('/admin/edit-post/<int:post_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_post(post_id):
    db = Database()
    if request.method == 'GET':
        post = db.get_post(post_id)
        if not post:
            flash('Пост не найден!', 'error')
            return redirect(url_for('manage_posts'))
        return render_template('edit_post.html', page_name='Редактировать пост', post=post)
    elif request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files['image']
        remove_image = request.form.get('remove_image') == 'on'
        try:
            post = db.get_post(post_id)
            if not post:
                flash('Пост не найден!', 'error')
                return redirect(url_for('manage_posts'))
            image_path = post['image'] if not remove_image else None
            if image and image.filename != '':
                ext = image.filename.split('.')[-1]
                filename = f"post_{post_id}.{ext}"
                new_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(new_path)
                if post['image']:
                    old_image = os.path.basename(post['image'])
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                image_path = os.path.join('uploads', filename).replace('\\', '/')
            elif remove_image and post['image']:
                old_image = os.path.basename(post['image'])
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_image)
                if os.path.exists(old_path):
                    os.remove(old_path)
                image_path = None
            db.update_post(post_id, title, content, image_path)
            flash('Пост успешно обновлен!', 'success')
        except Exception as e:
            flash(f'Ошибка при обновлении поста: {str(e)}', 'error')
        return redirect(url_for('manage_posts'))


@app.route('/admin/delete-post/<int:post_id>', methods=['POST'])
@admin_required
def admin_delete_post(post_id):
    db = Database()
    try:
        post = db.get_post(post_id)
        if post and post.get('image'):
            image_file = os.path.basename(post['image'])
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file)
            if os.path.exists(image_path):
                os.remove(image_path)
        db.delete_post(post_id)
        flash('Пост успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении поста: {str(e)}', 'error')
    return redirect(url_for('manage_posts'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', page_name='Страница не найдена'), 404


@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    db = Database()
    admin = db.get_admin(2)

    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_username = request.form.get('new_username', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Проверка текущего пароля для любых изменений
        if not current_password:
            flash('Введите текущий пароль для подтверждения изменений', 'error')
            return redirect(url_for('admin_settings'))

        hashed_current = hashlib.sha256(current_password.encode()).hexdigest()
        if hashed_current != admin['password']:
            flash('Неверный текущий пароль', 'error')
            return redirect(url_for('admin_settings'))

        # Флаги изменений
        username_changed = bool(new_username)
        password_changed = bool(new_password)

        if not username_changed and not password_changed:
            flash('Не указаны данные для обновления', 'info')
            return redirect(url_for('admin_settings'))

        # Валидация изменения пароля
        if password_changed:
            if new_password != confirm_password:
                flash('Новые пароли не совпадают', 'error')
                return redirect(url_for('admin_settings'))
            if len(new_password) < 6:
                flash('Пароль должен быть не менее 6 символов', 'error')
                return redirect(url_for('admin_settings'))

        try:
            # Раздельное обновление данных
            update_name = new_username if username_changed else None
            update_password = new_password if password_changed else None

            db.update_admin(1, name=update_name, password=update_password)

            # Формируем сообщение об успехе
            messages = []
            if username_changed:
                messages.append('имя пользователя')
                admin['name'] = new_username  # Обновляем локально для отображения
            if password_changed:
                messages.append('пароль')

            flash(f'Успешно обновлено: {", ".join(messages)}!', 'success')

            # Выход при смене пароля
            if password_changed:
                session.pop('authenticated', None)
                flash('Для входа используйте новый пароль', 'info')
                return redirect(url_for('admin_login'))

        except Exception as e:
            flash(f'Ошибка при обновлении: {str(e)}', 'error')
            app.logger.error(f'Error in admin_settings: {str(e)}')
            flash('Внутренняя ошибка сервера', 'error')
            return redirect(url_for('manage_posts'))

    return render_template('admin_settings.html', page_name='Настройки', admin=admin)


if __name__ == "__main__":
    app.run()