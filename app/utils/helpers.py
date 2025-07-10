import os
import secrets
from PIL import Image
from flask import flash, current_app
from flask_login import current_user

def save_picture(form_picture):
    import os, secrets
    from PIL import Image
    from flask import current_app

    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn