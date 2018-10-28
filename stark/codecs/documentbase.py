from urllib.parse import urlparse

from stark.codecs import BaseCodec, JSONSchemaCodec
from stark.compat import dict_type


class DocumentBaseCodec(BaseCodec):

    def get_paths(self, document, schema_defs=None):
        paths = dict_type()

        for link, name, sections in document.walk_links():
            path = urlparse(link.url).path
            operation_id = link.name
            tag = sections[0].name if sections else None
            method = link.method.lower()

            if path not in paths:
                paths[path] = {}
            paths[path][method] = self.get_operation(link, operation_id, tag=tag, schema_defs=schema_defs)

        return paths

    def get_operation(self, link, operation_id, tag=None, schema_defs=None):
        operation = {
            'operationId': operation_id
        }
        if link.title:
            operation['summary'] = link.title
        if link.description:
            operation['description'] = link.description
        if tag:
            operation['tags'] = [tag]
        if link.get_path_fields() or link.get_query_fields():
            operation['parameters'] = [
                self.get_parameter(field, schema_defs) for field in
                link.get_path_fields() + link.get_query_fields()
            ]
        if link.get_body_field():
            schema = link.get_body_field().schema
            if schema is None:
                content_info = {}
            else:
                content_info = {
                    'schema': JSONSchemaCodec().encode_to_data_structure(
                        schema,
                        schema_defs,
                        '#/components/schemas/'
                    )
                }

            operation['requestBody'] = {
                'content': {
                    link.encoding: content_info
                }
            }
        if link.response is not None:
            operation['responses'] = {
                str(link.response.status_code): {
                    'description': '',
                    'content': {
                        link.response.encoding: {
                            'schema': JSONSchemaCodec().encode_to_data_structure(
                                link.response.schema,
                                schema_defs,
                                '#/components/schemas/'
                            )
                        }
                    }
                }
            }
        return operation

    @staticmethod
    def get_parameter(field, schema_defs=None):
        parameter = {
            'name': field.name,
            'in': field.location
        }
        if field.required:
            parameter['required'] = True
        if field.description:
            parameter['description'] = field.description
        if field.schema:
            parameter['schema'] = JSONSchemaCodec().encode_to_data_structure(
                field.schema,
                schema_defs,
                '#/components/schemas/'
            )
        return parameter
