from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import FileField


class UploadForm(FlaskForm):
    file = FileField(validators=[FileRequired()])

    class Meta:
        csrf = False
