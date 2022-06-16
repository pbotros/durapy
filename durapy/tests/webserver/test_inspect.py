import dataclasses
from typing import List

from durapy.webserver._inspect import _extract_flattened_field_descriptions_class, \
    populate_from_field_descriptions_class
from durapy.command.model import BaseCommand


@dataclasses.dataclass
class Nested:
    nested_int: int
    nested_str: str
    nested_list_int: List[int] = dataclasses.field(default_factory=list)

@dataclasses.dataclass
class TestCommandPrint(BaseCommand):
    msg: str
    nested: Nested

    @staticmethod
    def type() -> str:
        return 'PRINT'


class TestInspect2:
    def test_works(self):
        print()
        from pprint import pprint
        instance = TestCommandPrint(
            msg='msg',
            nested=Nested(
                nested_int=123, nested_str='nested',
                nested_list_int=[1, 2, 35]))
        pprint(_extract_flattened_field_descriptions_class(
            clazz=TestCommandPrint,
            existing_instance=instance,
        ))

        print(populate_from_field_descriptions_class(
            clazz=TestCommandPrint,
            id_value_map={
                'msg': 'asdf',
                'nested.nested_int': 123,
                'nested.nested_str': 'zxcv',
                # 'nested.nested_list_int': json.dumps([1, 2, 5]),
            }
        ))