from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import FileField, IntegerField
from wtforms.validators import Optional


class UploadForm(FlaskForm):
    file = FileField(validators=[FileRequired()])
    expires_in = IntegerField(validators=[Optional()])

    class Meta:
        csrf = False
