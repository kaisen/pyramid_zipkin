# -*- coding: utf-8 -*-
from py_zipkin.exception import ZipkinError
from py_zipkin.zipkin import zipkin_span

from pyramid_zipkin.request_helper import create_zipkin_attr
from pyramid_zipkin.request_helper import get_binary_annotations


def zipkin_tween(handler, registry):
    """
    Factory for pyramid tween to handle zipkin server logging. Note that even
    if the request isn't sampled, Zipkin attributes are generated and pushed
    into threadlocal storage, so `create_http_headers_for_new_span` and
    `zipkin_span` will have access to the proper Zipkin state.

    :param handler: pyramid request handler
    :param registry: pyramid app registry

    :returns: pyramid tween
    """
    def tween(request):
        # Creates zipkin_attrs and attaches a zipkin_trace_id attr to the request
        zipkin_attrs = create_zipkin_attr(request)

        if 'zipkin.transport_handler' in request.registry.settings:
            transport_handler = request.registry.settings[
                'zipkin.transport_handler']
        else:
            raise ZipkinError(
                "`zipkin.transport_handler` is a required config property, which"
                " is missing. It is a callback method which takes a message as a"
                " param and logs it via scribe/kafka."
            )

        service_name = request.registry.settings.get('service_name', 'unknown')
        span_name = '{0} {1}'.format(request.method, request.path)

        with zipkin_span(
            service_name=service_name,
            span_name=span_name,
            zipkin_attrs=zipkin_attrs,
            transport_handler=transport_handler,
            port=request.server_port,
        ) as zipkin_context:
            response = handler(request)
            zipkin_context.update_binary_annotations_for_root_span(
                get_binary_annotations(request, response),
            )
            return response

    return tween
