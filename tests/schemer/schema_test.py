from schemer import Schema, Array
from schemer.exceptions import ValidationException, SchemaFormatException
from schemer.validators import one_of, lte, gte, length
import unittest
from mock import patch
from datetime import datetime
from sample import blog_post_schema, stubnow, valid_doc


class TestSchemaVerification(unittest.TestCase):

    def assert_spec_invalid(self, spec, path):
        for strict in [True, False]:
            with self.assertRaises(SchemaFormatException) as cm:
                Schema(spec, strict)
            self.assertEqual(path, cm.exception.path)

    def test_requires_field_spec_dict(self):
        self.assert_spec_invalid({"author": 45}, 'author')

    def test_missing_type(self):
        self.assert_spec_invalid({"author": {}}, 'author')

    def test_type_can_be_a_type(self):
        Schema({"author": {'type': str}})

    def test_type_can_be_another_schema(self):
        Schema({"author": {'type': Schema({
                    'first': {'type': str},
                    'last': {'type': str}
                })}})

    def test_type_cannot_be_an_instance(self):
        self.assert_spec_invalid({"author": {'type': "wrong"}}, 'author')

    def test_required_should_be_a_boolean(self):
        self.assert_spec_invalid(
            {
                "author": {'type': int, 'required': 23}
            },
            'author')

    def test_nullable_should_be_a_boolean(self):
        self.assert_spec_invalid(
            {
                "author": {'type': int, 'nullable': 23}
            },
            'author')


    def test_single_validation_function(self):
        Schema({'some_field': {'type':int, "validates":one_of(['a', 'b'])}})

    def test_multiple_validation_functions(self):
        Schema({'some_field': {'type':int, "validates":[gte(1), lte(10)]}})

    def test_invalid_validation(self):
        self.assert_spec_invalid(
            {'some_field': {'type':int, "validates":'wrong'}},
            'some_field')

    def test_invalid_validation_in_validation_list(self):
        self.assert_spec_invalid(
            {'some_field': {'type':int, "validates":[gte(1), 'wrong']}},
            'some_field')

    def test_incorrect_validator_arg_spec(self):
        def bad_validator():
            pass

        self.assert_spec_invalid(
            {'some_field': {'type':int, "validates":bad_validator}},
            'some_field')

        self.assert_spec_invalid(
            {'some_field': {'type':int, "validates":[bad_validator, gte(1)]}},
            'some_field')

    def test_unsupported_keys(self):
        self.assert_spec_invalid(
            {
                "somefield": {"type":int, "something":"wrong"},
                "otherfield": {"type":int}
            },
            'somefield')

    def test_default_value_of_correct_type(self):
        Schema({'num_wheels':{'type':int, 'default':4}})

    def test_default_value_of_incorrect_type(self):
        self.assert_spec_invalid(
            {'num_wheels':{'type':int, 'default':'wrong'}},
            'num_wheels')

    def test_default_value_accepts_function(self):
        def default_fn():
            return 4

        Schema({'num_wheels':{'type':int, 'default':default_fn}})

    def test_spec_wrong_type(self):
        self.assert_spec_invalid(
            {
                "items": []
            },
            'items')
        self.assert_spec_invalid(
            {
                "items": "wrong"
            },
            'items')

    def test_nested_schema_cannot_have_default(self):
        self.assert_spec_invalid(
            {
                "content": {'type': Schema({
                    "somefield": {"type": int}
                }), "default": {}}
            },
            'content')

    def test_nested_schema_cannot_have_validation(self):
        def some_func():
            pass
        self.assert_spec_invalid(
            {
                "content": {'type': Schema({
                    "somefield": {"type": int}
                }), "validates": some_func}
            },
            'content')

    def test_array_of_ints(self):
        Schema({
            "numbers": {"type": Array(int)}
        })

    def test_array_of_strings_with_default(self):
        Schema({
            "fruit": {'type': Array(basestring), "default": ['apple', 'orange']}
        })

    def test_array_of_strings_with_invalid_default(self):
        self.assert_spec_invalid({
            "fruit": {'type': Array(basestring), "default": 'not a list'}
        }, 'fruit')

    def test_array_of_strings_with_invalid_default_content(self):
        self.assert_spec_invalid({
            "nums": {'type': Array(int), "default": ['not an int']}
        }, 'nums')

    def test_invalid_array_with_value_not_type(self):
        self.assert_spec_invalid({
                "items": {"type": Array(1)}
            },
            'items')

    def test_array_validation(self):
        Schema({
            "fruit": {'type': Array(basestring), "validates": length(1, 2)}
        })


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.document = valid_doc()

    def assert_document_paths_invalid(self, document, paths):
        with self.assertRaises(ValidationException) as cm:
            blog_post_schema.validate(document)
        self.assertListEqual(paths, cm.exception.errors.keys())

    def test_valid_document(self):
        blog_post_schema.validate(self.document)

    def test_missing_required_field(self):
        del self.document['author']
        self.assert_document_paths_invalid(self.document, ['author'])

    def test_missing_required_array_field(self):
        del self.document['comments']
        self.assert_document_paths_invalid(self.document, ['comments'])

    def test_incorrect_type(self):
        self.document['author'] = 33
        self.assert_document_paths_invalid(self.document, ['author'])

    def test_mixed_type(self):
        self.document['misc'] = "a string"
        blog_post_schema.validate(self.document)
        self.document['misc'] = 32
        blog_post_schema.validate(self.document)

    def test_mixed_type_instance_incorrect_type(self):
        self.document['linked_id'] = 123.45
        self.assert_document_paths_invalid(self.document, ['linked_id'])

    def test_missing_embedded_document(self):
        del self.document['content']
        self.assert_document_paths_invalid(self.document, ['content'])

    def test_missing_required_field_in_embedded_document(self):
        del self.document['content']['title']
        self.assert_document_paths_invalid(self.document, ['content.title'])

    def test_missing_required_field_in_embedded_collection(self):
        del self.document['comments'][0]['commenter']
        self.assert_document_paths_invalid(self.document, ['comments.0.commenter'])

    def test_multiple_missing_fields(self):
        del self.document['content']['title']
        del self.document['comments'][1]['commenter']
        del self.document['author']
        self.assert_document_paths_invalid(
            self.document,
            ['content.title', 'comments.1.commenter', 'author'])

    def test_embedded_collection_item_of_incorrect_type(self):
        self.document['tags'].append(55)
        self.assert_document_paths_invalid(self.document, ['tags.3'])

    def test_validation_failure(self):
        self.document['category'] = 'gardening'  # invalid category
        self.assert_document_paths_invalid(self.document, ['category'])

    def test_disallows_fields_not_in_schema(self):
        self.document['something'] = "extra"
        self.assert_document_paths_invalid(self.document, ['something'])

    def test_validation_of_array(self):
        self.document['tags'] = []
        self.assert_document_paths_invalid(self.document, ['tags'])


class TestDefaultApplication(unittest.TestCase):
    def setUp(self):
        self.document = {
            "author": {
                "first":    "John",
                "last":     "Humphreys"
            },
            "content": {
                "title": "How to make cookies",
                "text": "First start by pre-heating the oven..."
            },
            "category": "cooking",
            "comments": [
                {
                    "commenter": "Julio Cesar",
                    "email": "jcesar@test.com",
                    "comment": "Great post dude!"
                },
                {
                    "commenter": "Michael Andrews",
                    "comment": "My wife loves these."
                }
            ]
        }

    def test_apply_default_function(self):
        blog_post_schema.apply_defaults(self.document)
        self.assertEqual(stubnow(), self.document['creation_date'])

    def test_apply_default_value(self):
        blog_post_schema.apply_defaults(self.document)
        self.assertEqual(0, self.document['likes'])

    def test_apply_default_value_in_nested_document(self):
        blog_post_schema.apply_defaults(self.document)
        self.assertEqual(1, self.document['content']['page_views'])

    def test_apply_default_value_in_array(self):
        blog_post_schema.apply_defaults(self.document)
        self.assertEqual(0, self.document['comments'][0]['votes'])
        self.assertEqual(0, self.document['comments'][1]['votes'])

    def test_apply_default_value_for_array(self):
        blog_post_schema.apply_defaults(self.document)
        self.assertEqual(['blog'], self.document['tags'])

    def test_default_value_does_not_overwrite_existing(self):
        self.document['likes'] = 35
        self.document['creation_date'] = datetime(1980, 5, 3)
        blog_post_schema.apply_defaults(self.document)
        self.assertEqual(35, self.document['likes'])
        self.assertEqual(datetime(1980, 5, 3), self.document['creation_date'])
