# from mongoengine import ReferenceField, ListField
# from mongoengine.base import BaseDocument, DocumentMetaclass, get_document

from wtforms import fields, validators, StringField
# from flask_mongoengine.wtf import orm, fields as mongo_fields

from flask_admin import form
from flask_admin.model.form import FieldPlaceholder
from flask_admin.model.fields import InlineFieldList, AjaxSelectField, AjaxSelectMultipleField
from flask_admin.form.validators import FieldListInputRequired
from flask_admin._compat import iteritems

# from .fields import ModelFormField, MongoFileField, MongoImageField
# from .subdoc import EmbeddedForm
# from wtforms.utils import unset_value


class CommonField(StringField):
    pass
    # def process(self, formdata, data=unset_value):
    #     print(formdata)
    #     print(data)
    #     print('*'*80)
    #     return super().process(formdata, data)


def converts(*args):
    def _inner(func):
        func._converter_for = frozenset(args)
        return func
    return _inner


class ModelConverter(object):
    def __init__(self, converters=None):
        if not converters:
            converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, '_converter_for'):
                for classname in obj._converter_for:
                    converters[classname] = obj

        self.converters = converters

    def convert(self, model, field, field_args):
        kwargs = {
            'label': getattr(field, 'verbose_name', field.name),
            'description': getattr(field, 'help_text', None) or '',
            'validators': getattr(field, 'validators', None) or [],
            'filters': getattr(field, 'filters', None) or [],
            'default': field.default,
        }
        if field_args:
            kwargs.update(field_args)

        if kwargs['validators']:
            # Create a copy of the list since we will be modifying it.
            kwargs['validators'] = list(kwargs['validators'])

        if field.required:
            kwargs['validators'].append(validators.InputRequired())
        else:
            kwargs['validators'].append(validators.Optional())

        ftype = type(field).__name__

        if field.choices:
            kwargs['choices'] = field.choices

            if ftype in self.converters:
                kwargs["coerce"] = self.coerce(ftype)
            multiple_field = kwargs.pop('multiple', False)
            radio_field = kwargs.pop('radio', False)
            if multiple_field:
                return f.SelectMultipleField(**kwargs)
            if radio_field:
                return f.RadioField(**kwargs)
            return f.SelectField(**kwargs)

        ftype = type(field).__name__

        if hasattr(field, 'to_form_field'):
            return field.to_form_field(model, kwargs)

        if ftype in self.converters:
            return self.converters[ftype](model, field, kwargs)

    @classmethod
    def _string_common(cls, model, field, kwargs):
        if field.max_length or field.min_length:
            kwargs['validators'].append(
                validators.Length(max=field.max_length or -1,
                                  min=field.min_length or -1))

    @classmethod
    def _number_common(cls, model, field, kwargs):
        if field.max_value or field.min_value:
            kwargs['validators'].append(
                validators.NumberRange(max=field.max_value,
                                       min=field.min_value))

    @converts('StringField')
    def conv_String(self, model, field, kwargs):
        if field.regex:
            kwargs['validators'].append(validators.Regexp(regex=field.regex))
        self._string_common(model, field, kwargs)
        password_field = kwargs.pop('password', False)
        textarea_field = kwargs.pop('textarea', False) or not field.max_length
        if password_field:
            return f.PasswordField(**kwargs)
        if textarea_field:
            return f.TextAreaField(**kwargs)
        return f.StringField(**kwargs)

    @converts('URLField')
    def conv_URL(self, model, field, kwargs):
        kwargs['validators'].append(validators.URL())
        self._string_common(model, field, kwargs)
        return NoneStringField(**kwargs)

    @converts('EmailField')
    def conv_Email(self, model, field, kwargs):
        kwargs['validators'].append(validators.Email())
        self._string_common(model, field, kwargs)
        return NoneStringField(**kwargs)

    @converts('IntField')
    def conv_Int(self, model, field, kwargs):
        self._number_common(model, field, kwargs)
        return f.IntegerField(**kwargs)

    @converts('FloatField')
    def conv_Float(self, model, field, kwargs):
        self._number_common(model, field, kwargs)
        return f.FloatField(**kwargs)

    @converts('DecimalField')
    def conv_Decimal(self, model, field, kwargs):
        self._number_common(model, field, kwargs)
        return f.DecimalField(**kwargs)

    @converts('BooleanField')
    def conv_Boolean(self, model, field, kwargs):
        return f.BooleanField(**kwargs)

    @converts('DateTimeField')
    def conv_DateTime(self, model, field, kwargs):
        return f.DateTimeField(**kwargs)

    @converts('BinaryField')
    def conv_Binary(self, model, field, kwargs):
        # TODO: may be set file field that will save file`s data to MongoDB
        if field.max_bytes:
            kwargs['validators'].append(validators.Length(max=field.max_bytes))
        return BinaryField(**kwargs)

    @converts('DictField')
    def conv_Dict(self, model, field, kwargs):
        return DictField(**kwargs)

    @converts('ListField')
    def conv_List(self, model, field, kwargs):
        if isinstance(field.field, ReferenceField):
            return ModelSelectMultipleField(model=field.field.document_type, **kwargs)
        if field.field.choices:
            kwargs['multiple'] = True
            return self.convert(model, field.field, kwargs)
        field_args = kwargs.pop("field_args", {})
        unbound_field = self.convert(model, field.field, field_args)
        unacceptable = {
            'validators': [],
            'filters': [],
            'min_entries': kwargs.get('min_entries', 0)
        }
        kwargs.update(unacceptable)
        return f.FieldList(unbound_field, **kwargs)

    @converts('SortedListField')
    def conv_SortedList(self, model, field, kwargs):
        # TODO: sort functionality, may be need sortable widget
        return self.conv_List(model, field, kwargs)

    @converts('GeoLocationField')
    def conv_GeoLocation(self, model, field, kwargs):
        # TODO: create geo field and widget (also GoogleMaps)
        return

    @converts('ObjectIdField')
    def conv_ObjectId(self, model, field, kwargs):
        return

    @converts('EmbeddedDocumentField')
    def conv_EmbeddedDocument(self, model, field, kwargs):
        kwargs = {
            'validators': [],
            'filters': [],
            'default': field.default or field.document_type_obj,
        }
        form_class = model_form(field.document_type_obj, field_args={})
        return f.FormField(form_class, **kwargs)

    @converts('ReferenceField')
    def conv_Reference(self, model, field, kwargs):
        return ModelSelectField(model=field.document_type, **kwargs)

    @converts('GenericReferenceField')
    def conv_GenericReference(self, model, field, kwargs):
        return

    def coerce(self, field_type):
        coercions = {
            "IntField": int,
            "BooleanField": bool,
            "FloatField": float,
            "DecimalField": decimal.Decimal,
            "ObjectIdField": ObjectId
        }
        return coercions.get(field_type, unicode)


class CustomModelConverter(ModelConverter):
    """
        Customized MongoEngine form conversion class.

        Injects various Flask-Admin widgets and handles lists with
        customized InlineFieldList field.
    """

    def __init__(self, view):
        super(CustomModelConverter, self).__init__()

        self.view = view

    def _get_field_override(self, name):
        form_overrides = getattr(self.view, 'form_overrides', None)

        if form_overrides:
            return form_overrides.get(name)

        return None

    def _get_subdocument_config(self, name):
        config = getattr(self.view, '_form_subdocuments', {})

        p = config.get(name)
        if not p:
            return EmbeddedForm()

        return p

    def _convert_choices(self, choices):
        for c in choices:
            if isinstance(c, tuple):
                yield c
            else:
                yield (c, c)

    def clone_converter(self, view):
        return self.__class__(view)

    def convert(self, model, field, field_args):
        # Check if it is overridden field
        if isinstance(field, FieldPlaceholder):
            return form.recreate_field(field.field)

        kwargs = {
            'label': getattr(field, 'verbose_name', None),
            'description': getattr(field, 'help_text', ''),
            'validators': [],
            'filters': [],
            'default': field.default
        }

        if field_args:
            kwargs.update(field_args)

        if kwargs['validators']:
            # Create a copy of the list since we will be modifying it.
            kwargs['validators'] = list(kwargs['validators'])

        if field.required:
            if isinstance(field, ListField):
                kwargs['validators'].append(FieldListInputRequired())
            else:
                kwargs['validators'].append(validators.InputRequired())
        elif not isinstance(field, ListField):
            kwargs['validators'].append(validators.Optional())

        ftype = type(field).__name__

        if field.choices:
            kwargs['choices'] = list(self._convert_choices(field.choices))

            if ftype in self.converters:
                kwargs["coerce"] = self.coerce(ftype)
            if kwargs.pop('multiple', False):
                return fields.SelectMultipleField(**kwargs)
            return fields.SelectField(**kwargs)

        ftype = type(field).__name__

        if hasattr(field, 'to_form_field'):
            return field.to_form_field(model, kwargs)

        override = self._get_field_override(field.name)
        if override:
            return override(**kwargs)

        if ftype in self.converters:
            return self.converters[ftype](model, field, kwargs)

    # @orm.converts('DateTimeField')
    # def conv_DateTime(self, model, field, kwargs):
    #     kwargs['widget'] = form.DateTimePickerWidget()
    #     return orm.ModelConverter.conv_DateTime(self, model, field, kwargs)

    # @orm.converts('ListField')
    # def conv_List(self, model, field, kwargs):
    #     if field.field is None:
    #         raise ValueError('ListField "%s" must have field specified for model %s' % (field.name, model))

    #     if isinstance(field.field, ReferenceField):
    #         loader = getattr(self.view, '_form_ajax_refs', {}).get(field.name)
    #         if loader:
    #             return AjaxSelectMultipleField(loader, **kwargs)

    #         kwargs['widget'] = form.Select2Widget(multiple=True)
    #         kwargs.setdefault('validators', []).append(validators.Optional())

    #         # TODO: Support AJAX multi-select
    #         doc_type = field.field.document_type
    #         return mongo_fields.ModelSelectMultipleField(model=doc_type, **kwargs)

    #     # Create converter
    #     view = self._get_subdocument_config(field.name)
    #     converter = self.clone_converter(view)

    #     if field.field.choices:
    #         kwargs['multiple'] = True
    #         return converter.convert(model, field.field, kwargs)

    #     unbound_field = converter.convert(model, field.field, {})
    #     return InlineFieldList(unbound_field, min_entries=0, **kwargs)

    # @orm.converts('EmbeddedDocumentField')
    # def conv_EmbeddedDocument(self, model, field, kwargs):
    #     # FormField does not support validators
    #     kwargs['validators'] = []

    #     view = self._get_subdocument_config(field.name)

    #     form_opts = form.FormOpts(widget_args=getattr(view, 'form_widget_args', None),
    #                               form_rules=view._form_rules)

    #     form_class = view.get_form()
    #     if form_class is None:
    #         converter = self.clone_converter(view)
    #         form_class = get_form(field.document_type_obj, converter,
    #                               base_class=view.form_base_class or form.BaseForm,
    #                               only=view.form_columns,
    #                               exclude=view.form_excluded_columns,
    #                               field_args=view.form_args,
    #                               extra_fields=view.form_extra_fields)

    #         form_class = view.postprocess_form(form_class)

    #     return ModelFormField(field.document_type_obj, view, form_class, form_opts=form_opts, **kwargs)

    # @orm.converts('ReferenceField')
    # def conv_Reference(self, model, field, kwargs):
    #     kwargs['allow_blank'] = not field.required

    #     loader = getattr(self.view, '_form_ajax_refs', {}).get(field.name)
    #     if loader:
    #         return AjaxSelectField(loader, **kwargs)

    #     kwargs['widget'] = form.Select2Widget()

    #     return orm.ModelConverter.conv_Reference(self, model, field, kwargs)

    # @orm.converts('FileField')
    # def conv_File(self, model, field, kwargs):
    #     return MongoFileField(**kwargs)

    # @orm.converts('ImageField')
    # def conv_image(self, model, field, kwargs):
    #     return MongoImageField(**kwargs)


def get_form(model, converter,
             base_class=form.BaseForm,
             only=None,
             exclude=None,
             field_args=None,
             extra_fields=None):
    """
    Create a wtforms Form for a given mongoengine Document schema::

        from flask_mongoengine.wtf import model_form
        from myproject.myapp.schemas import Article
        ArticleForm = model_form(Article)

    :param model:
        A mongoengine Document schema class
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments used
        to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """

    # if isinstance(model, str):
        # model = get_document(model)

    # if not isinstance(model, (BaseDocument, DocumentMetaclass)):
    #     raise TypeError('Model must be a mongoengine Document schema')

    field_args = field_args or {}

    # Find properties
    # properties = sorted(((k, v) for k, v in iteritems(model._fields)),
    #                     key=lambda v: v[1].creation_counter)
    # print(dir(model))
    # print(model)
    properties = dict(model._reverse_name_map.filtered())
    #                     key=lambda v: v[1].creation_counter)

    # print(model)
    # print('*'*80)

    if only:
        props = dict(properties)

        def find(name):
            if extra_fields and name in extra_fields:
                return FieldPlaceholder(extra_fields[name])

            p = props.get(name)
            if p is not None:
                return p

            raise ValueError('Invalid model property name %s.%s' % (model, name))

        properties = ((p, find(p)) for p in only)
    elif exclude:
        properties = (p for p in properties if p[0] not in exclude)

    # Create fields
    field_dict = {}
    for name, p in properties:
        # field = converter.convert(model, p, field_args.get(name))
        field = CommonField(label=p)
        if field is not None:
            field_dict[name] = field

    # Contribute extra fields
    if not only and extra_fields:
        for name, field in iteritems(extra_fields):
            field_dict[name] = form.recreate_field(field)

    field_dict['model_class'] = model
    return type(model.__name__ + 'Form', (base_class,), field_dict)
