# import pymongo
from bson.objectid import ObjectId

from flask import Flask
import flask_admin as admin

from wtforms import form, fields

from flask_admin.form import Select2Widget
from flask_admin.contrib.humbledb import ModelView, filters
from flask_admin.model.fields import InlineFormField, InlineFieldList
from humbledb import Mongo, Document


# Create application
app = Flask(__name__)

# Create dummy secrey key so we can use sessions
app.config['SECRET_KEY'] = '123456790'
app.config['FLASK_ADMIN_SWATCH'] = 'slate'


class Connection(Mongo):
    config_host = '192.168.8.176'
    config_port = 27017


# models
class User(Document):
    config_database = 'tby'
    config_collection = 'users'

    name = 'nk'
    mobile = 'm'


# User admin
# class InnerForm(form.Form):
#     name = fields.StringField('Name')
#     test = fields.StringField('Test')


# class UserForm(form.Form):
#     name = fields.StringField('Name')
#     mobile = fields.StringField('Mobile')
#     # email = fields.StringField('Email')
#     # password = fields.StringField('Password')

#     # Inner form
#     inner = InlineFormField(InnerForm)

#     # Form list
#     form_list = InlineFieldList(InlineFormField(InnerForm))


class UserView(ModelView):
    column_list = (User.name, User.mobile, 'hello')
    column_formatters = {
        'hello': lambda v, c, m, p: 'world'
    }
    column_labels = {
        User.name: 'Name',
        User.mobile: 'Mobile',
    }

    column_default_sort = (User.name, True)
    column_sortable_list = (User.mobile,)

    column_searchable_list = (User.name, User.mobile)
    column_filters = (filters.FilterEqual(User.name, 'Name'),
                      filters.FilterNotEqual(User.name, 'Name'),
                      filters.FilterLike(User.name, 'Name'),
                      filters.FilterNotLike(User.name, 'Name'),
                      filters.FilterEqual(User.mobile, 'Mobile'))

    can_view_details = True
    column_details_list = (User.name, User.mobile)

    can_export = True
    column_export_list = (User.name, User.mobile, 'hello')

    simple_list_pager = True
    page_size = 10

    form_columns = (User.name, User.mobile)
    form_args = {
        User.name: {
            'label': 'Name',
        },
        User.mobile: {
            'label': 'Mobile',
        },
    }

    # form = UserForm

# Tweet view
# class TweetForm(form.Form):
#     name = fields.StringField('Name')
#     user_id = fields.SelectField('User', widget=Select2Widget())
#     text = fields.StringField('Text')

#     testie = fields.BooleanField('Test')


# class TweetView(ModelView):
#     column_list = ('name', 'user_name', 'text')
#     column_sortable_list = ('name', 'text')

#     column_filters = (filters.FilterEqual('name', 'Name'),
#                       filters.FilterNotEqual('name', 'Name'),
#                       filters.FilterLike('name', 'Name'),
#                       filters.FilterNotLike('name', 'Name'),
#                       filters.BooleanEqualFilter('testie', 'Testie'))

#     column_searchable_list = ('name', 'text')

#     form = TweetForm

#     def get_list(self, *args, **kwargs):
#         count, data = super(TweetView, self).get_list(*args, **kwargs)

#         # Grab user names
#         query = {'_id': {'$in': [x['user_id'] for x in data]}}
#         users = db.user.find(query, projection=('name',))

#         # Contribute user names to the models
#         users_map = dict((x['_id'], x['name']) for x in users)

#         for item in data:
#             item['user_name'] = users_map.get(item['user_id'])

#         return count, data

#     # Contribute list of user choices to the forms
#     def _feed_user_choices(self, form):
#         users = db.user.find(projection=('u',))
#         form.user_id.choices = [(str(x['_id']), x['name']) for x in users]
#         return form

#     def create_form(self):
#         form = super(TweetView, self).create_form()
#         return self._feed_user_choices(form)

#     def edit_form(self, obj):
#         form = super(TweetView, self).edit_form(obj)
#         return self._feed_user_choices(form)

#     # Correct user_id reference before saving
#     def on_model_change(self, form, model):
#         user_id = model.get('user_id')
#         model['user_id'] = ObjectId(user_id)

#         return model


# Flask views
@app.route('/')
def index():
    return '<a href="/admin/">Click me to get to Admin!</a>'


if __name__ == '__main__':
    # Create admin
    admin = admin.Admin(app, name='Example: HumbleDB', template_mode='bootstrap3')

    # Add views
    admin.add_view(UserView(Connection, User, name='User'))
    # admin.add_view(TweetView(db.tweet, 'Tweets'))

    # Start app
    app.run(debug=True)
