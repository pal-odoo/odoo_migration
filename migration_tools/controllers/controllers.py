# -*- coding: utf-8 -*-
from odoo import http

# class MigrationTools(http.Controller):
#     @http.route('/migration_tools/migration_tools/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/migration_tools/migration_tools/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('migration_tools.listing', {
#             'root': '/migration_tools/migration_tools',
#             'objects': http.request.env['migration_tools.migration_tools'].search([]),
#         })

#     @http.route('/migration_tools/migration_tools/objects/<model("migration_tools.migration_tools"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('migration_tools.object', {
#             'object': obj
#         })