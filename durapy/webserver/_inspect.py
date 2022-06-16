import dataclasses
import distutils.util
import json
import typing
from enum import Enum

from dataclasses_json import DataClassJsonMixin
from more_itertools import only  # type: ignore

CommandT = typing.TypeVar('CommandT', bound='Command')


@dataclasses.dataclass
class FieldDescription(DataClassJsonMixin):
    """
    "Flattened" field descriptions, where the `id` is a '.'-delimited identifier referring to nested classes within
    a given class. Suitable for displaying / editing dataclasses in a GUI.
    """

    # '.' delimited identifier referring to this field. For example, for a non-nested field, this would be "field_name",
    # but if the field is nested in a subfield named `nested`, this id would be `nested.field_name`.
    id: str

    # The actual field name of this field, disregarding nesting.
    basename: str

    # Whether this field is optional
    optional: bool

    # Type hint for this field (e.g. [int])
    hint: str

    # Is the field a boolean?
    is_bool: bool

    # Default value of the field, if there is a default
    placeholder: typing.Optional[str]

    # Current value of the field, if given an instance
    val: typing.Optional[str]

    # For use in Enums: allowed (string) options for this field
    allowed: typing.Optional[typing.List[str]]

    # Name of the parent class holding this field
    parent_class_name: str

@dataclasses.dataclass
class FieldDescriptionForPopulating(DataClassJsonMixin):
    # A subset of FieldDescription, just containing the bare minimum fields to populate a new command

    # '.' delimited identifier referring to this field. For example, for a non-nested field, this would be "field_name",
    # but if the field is nested in a subfield named `nested`, this id would be `nested.field_name`.
    id: str

    val: typing.Optional[str]


def populate_from_field_descriptions_class(
        clazz: typing.Type[CommandT],
        field_descriptions: typing.List[typing.Union[FieldDescription, FieldDescriptionForPopulating]]) -> CommandT:
    exploded_params = {}

    for field_description in field_descriptions:
        key = field_description.id
        val = field_description.val
        nested_keys = key.split('.')
        d = exploded_params
        for nested_key in nested_keys[:-1]:
            if nested_key in d:
                d = d[nested_key]
            else:
                d[nested_key] = {}
                d = d[nested_key]
        d[nested_keys[-1]] = val

    clazz_dict = {}
    _populate_clazz_dict(exploded_params, clazz_dict, clazz)
    return clazz.from_dict(clazz_dict)


def _populate_clazz_dict(params_dict, clazz_dict, clazz: typing.Type[CommandT]):
    for key, val in params_dict.items():
        val_dataclass_type = only([d for d in dataclasses.fields(clazz) if d.name == key]).type
        val_dataclass_type = _extract_from_optional(val_dataclass_type)
        maybe_iterable_type = _extract_from_iterable(val_dataclass_type)
        if isinstance(val, dict):
            clazz_dict[key] = {}
            _populate_clazz_dict(val, clazz_dict=clazz_dict[key], clazz=val_dataclass_type)
        elif val_dataclass_type == bool and not isinstance(val, bool):
            clazz_dict[key] = bool(distutils.util.strtobool(val))
        elif maybe_iterable_type is not None:
            # Single to double quotes
            clazz_dict[key] = json.loads(val.replace("'", '"'))
        else:
            clazz_dict[key] = val_dataclass_type(val)


def extract_flattened_field_descriptions_class(
        clazz: typing.Type[CommandT], existing_instance: typing.Optional[CommandT]) -> typing.List[FieldDescription]:
    properties = []
    for field in dataclasses.fields(clazz):
        if dataclasses.is_dataclass(field.type):
            existing_nested = getattr(existing_instance, field.name) if existing_instance is not None else None
            nested_properties = extract_flattened_field_descriptions_class(field.type, existing_nested)
            for nested_property in nested_properties:
                nested_property = dataclasses.replace(nested_property, **{
                    'id': f'{field.name}.{nested_property.id}',
                })
                properties.append(nested_property)
        else:
            d = {
                'val': None,
                'placeholder': None,
                'allowed': None,
            }

            field_type = _extract_from_optional(field.type)
            # It was an Optional if the field type had to change
            d['optional'] = field_type != field.type

            maybe_iterable_type = _extract_from_iterable(field_type)
            d.update({
                'id': field.name,
                'basename': field.name,
                'parent_class_name': clazz.__name__
            })
            if maybe_iterable_type is not None:
                d['hint'] = f'[{maybe_iterable_type.__name__}]'
                d['is_bool'] = False
            else:
                d['hint'] = f'[{field_type.__name__}]'
                d['is_bool'] = issubclass(field_type, bool)
                if issubclass(field_type, Enum):
                    d['allowed'] = [e.name for e in field_type]

            if existing_instance is not None:
                attr = getattr(existing_instance, field.name)
                if attr is not None:
                    if maybe_iterable_type is not None:
                        attr = json.dumps(attr)
                    elif issubclass(field_type, Enum):
                        attr = attr.name
                    d['val'] = attr
            elif field.default != dataclasses.MISSING:
                default_val = field.default
                if isinstance(default_val, Enum):
                    d['placeholder'] = default_val.name
                else:
                    d['placeholder'] = str(default_val)

            properties.append(FieldDescription(**d))
    return properties


def _extract_from_optional(t: type) -> type:
    if hasattr(t, '__origin__') and \
            t.__origin__ == typing.Union and \
            len(t.__args__) == 2 and \
            any([a == type(None) for a in t.__args__]):
        return only([a for a in t.__args__ if a != type(None)])
    return t


def _extract_from_iterable(t: type) -> typing.Optional[type]:
    if hasattr(t, '__origin__') and \
            hasattr(t.__origin__, '__iter__'):
        return t.__origin__
    return None
