# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.misc import groupby

VIEW_TYPE_SEQUENCES = {
        'tree': 1,
        'kanban': 2,
        'form': 3,
        'graph': 4,
        'pivot': 5,
        'calendar': 6,
    'diagram': 7,
        'gantt': 8,
    'search': 9,
    'qweb': 10,
        'cohort': 11,
        'dashboard': 12,
        'grid': 13,
        'activity': 14,
}


class MigrationModuleViews(models.Model):
    _name = 'migration.module.views'

    module_id = fields.Many2one('ir.module.module', required=True)  # , index=True
    root_menu_item_id = fields.Many2one('ir.ui.menu', string='Main Menu Item',
        readonly=True)
    sub_menu_item_ids = fields.One2many('ir.ui.menu', 'migration_module_view_id', string='Sub Menu Items',
        readonly=True)
    action_window_views_ids = fields.One2many('ir.actions.act_window.view', 'migration_module_view_id',
        string='Action Views')
    action_window_ids = fields.One2many('ir.actions.act_window', 'migration_module_view_id', string='Action Windows',
        readonly=True)
    views_created = fields.Boolean('Views Created', compute='_compute_views_created', readonly=True)

    @api.depends('root_menu_item_id')
    def _compute_views_created(self):
        for rec in self:
            rec.views_created = bool(rec.root_menu_item_id)

    def create_module_items(self):
        self.ensure_one()
        # View = self.env['ir.ui.view']
        # Menu = self.env['ir.ui.menu']
        # ActWindow = self.env['ir.actions.act_window']
        # ActWindowView = self.env['ir.actions.act_window.view']

        # 1. Create main menu item
        # 2. Search all views and related actions
        # 2.5. Create non existing actions
        # 3. Add sub menu items with main menu item as parent , linked to related actions

        # Create main menu item
        if not self.root_menu_item_id:
            self.root_menu_item_id = self.env['ir.ui.menu'].create({
                'name': self.module_id.name,
                'parent_id': self.env.ref('migration_tools.menu_root').id,
                'module_name': self.module_id.name,
                'migration_module_view_id': self.id,
            })

        # Search all views and related actions for module_id
        existing_action_window_ids = self.env['ir.model.data'].search([
            ('module', '=', self.module_id.name),
            ('model', '=', 'ir.actions.act_window'),
        ]).mapped('res_id')
        sub_menus = self._create_menu_items(self.env['ir.actions.act_window'].browse(existing_action_window_ids))

        existing_view_ids = self.env['ir.model.data'].search([
            ('module', '=', self.module_id.name),
            ('model', '=', 'ir.ui.view'),
        ]).mapped('res_id')
        views = self.env['ir.ui.view'].browse(existing_view_ids)
        grouped_views = groupby(views, lambda v: v.model)
        # TODO Que fait-on avec les vues qui n'ont pas de 'model'?
        for model, views in grouped_views:
            self._create_records(model, views)

        # Creates Action Reports
        existing_action_report_ids = self.env['ir.model.data'].search([
            ('module', '=', self.module_id.name),
            ('model', '=', 'ir.actions.report'),
        ]).mapped('res_id')

        self.report_menu_item_id = self.env['ir.ui.menu'].create({
            'name': '---Reports---',
            'parent_id': self.root_menu_item_id.id,
            'module_name': self.module_id.name,
            'migration_module_view_id': self.id,
        })
        # for act_report in self.env['ir.actions.report'].browse(existing_action_report_ids):
        #     <ir.ui.menu>.action = 'ir.actions.report,200'
        self.env['ir.ui.menu'].create([{
                'name': '<%s> %s' % (act_report.model, act_report.report_name),
                'parent_id': self.report_menu_item_id.id,
                'action': 'ir.actions.report,%d' % (act_report.id,),
                'sequence': seq * 10,
                'migration_module_view_id': self.id,
            } for seq, act_report in enumerate(self.env['ir.actions.report'].browse(existing_action_report_ids))
        ])
        # <ir.actions.report>.model
        # <ir.actions.report>.report_name
        # action = fields.Reference(selection=[('ir.actions.report'

    def delete_module_items(self):
        self.ensure_one()
        self.action_window_ids.filtered(lambda aw: aw.created_for_migration).unlink()
        self.action_window_views_ids.unlink()
        self.sub_menu_item_ids.unlink()
        self.root_menu_item_id.unlink()


    def _create_records(self, model, views):
        Menu = self.env['ir.ui.menu']
        ActWindow = self.env['ir.actions.act_window']
        ActWindowView = self.env['ir.actions.act_window.view']

        def get_parent_view(view):
            return get_parent_view(view.inherit_id) if view.inherit_id else view
            # if view.inherit_id:
            #     return get_parent_view(view.inherit_id)
            # return view

        other_action_windows = ActWindow.search([('view_id.id', 'in', [v.id for v in views])])

        # TODO Manage views that inherit other views
        # Create non existing actions and get existing ones
        # existing_action_windows = self.env['ir.model.data'].search([
        #     ('module', '=', self.module_id.name),
        #     ('model', '=', 'ir.actions.act_window'),
        # ])  # TODO Doit être mis dans la fonction appelante
        # if existing_action_windows:
        #     import ipdb; ipdb.set_trace()

        # view_modes = {}
        concat_mods = ''
        new_action_window_views = ActWindowView
        search_views = []
        for i, view in enumerate(views):
            parent_view = get_parent_view(view)
            if parent_view.type == 'search':
                search_views.append(parent_view)
                continue
            elif parent_view.type == 'qweb':
                continue  # TODO
            elif parent_view.type == 'diagram':
                continue  # TODO
            # else:
            #     raise UserError('Unknown view type: "%s".' % parent_view.type)

            awv = ActWindowView.create({
                'view_mode': parent_view.type,
                # 'act_window_id': action_id.id,
                'view_id': parent_view.id,
                'sequence': VIEW_TYPE_SEQUENCES[parent_view.type]*10 + i,
                'migration_module_view_id': self.id,
            })
            # awv.view_mode not lst_view_modes:
            #     lst_view_modes.append(awv.view_mode)
            new_action_window_views |= awv
            # view_modes.setdefault(awv.view_mode, []).append(awv)



        # existing_actwin_views = other_action_windows.mapped('view_id')
        new_action_windows = ActWindow
        grouped_modes = []
        # [
        #  [['tree', 'form', 'kanban'], [res1, res2]],
        #  [['tree'], [res3]],
        # ]
        for act_win_vw in new_action_window_views:
            for modes, recs in grouped_modes:
                if act_win_vw.view_mode not in modes:
                    modes.append(act_win_vw.view_mode)
                    recs.append(act_win_vw)
                    break
            else:
                grouped_modes.append([[act_win_vw.view_mode], [act_win_vw]])
        # for modes, _ in grouped_modes:
        #     if 'tree' not in modes:
        #         modes.insert(0, 'tree')


        # for modes, act_win_vws in grouped_modes:

        # for view in views:
        # # for view in views - existing_actwin_views:
            # print(view.type)
            # parent_view = get_parent_view(view)
            # if view.type == 'search':
            #     # 'search_view_id' <--> 'view_id'
            #     continue  # TODO Manage view.type == 'search'
        act_windows = []
        for modes, act_win_vws in grouped_modes:
            search_view = search_views.pop() if search_views else None
            act_windows.append({
                'name': 'action.migration.%s' % act_win_vws[0].view_id.name,
                'res_model': model,  # TODO Attention! views peut ne pas avoir de 'model'
                'context': '{}',
                'type': 'ir.actions.act_window',
                'view_mode': ','.join(modes + ([search_view.type] if search_view else [])),
                # 'view_mode': 'tree,form,kanban',  # TODO
                'view_type': 'form',  # view.type,

                # 'view_id': view.id,
                'view_ids': [(4, rec.id) for rec in act_win_vws],
                'search_view_id': search_view.id if search_view else None,
                'created_for_migration': True,
                'migration_module_view_id': self.id,
            })
        new_action_windows = ActWindow.create(act_windows)
# new_action_windows = ActWindow.create([{
#         'name': 'action.migration.%s' % act_win_vws[0].view_id.name,
#         'res_model': model,  # TODO Attention! views peut ne pas avoir de 'model'
#         'context': '{}',
#         'type': 'ir.actions.act_window',
#         'view_mode': ','.join(modes),
#         # 'view_mode': 'tree,form,kanban',  # TODO
#         'view_type': 'form',  # view.type,

#         # 'view_id': view.id,
#         'view_ids': [(4, rec.id) for rec in act_win_vws],
#         'search_view_id': search_views.pop().id if search_views else None,
#         'created_for_migration': True,
#         'migration_module_view_id': self.id,
#     } for modes, act_win_vws in grouped_modes
# ])
        # TODO Should we do sth with this??? act_win_vws = self.env['ir.actions.act_window.view'].search([('view_id', 'in', views.ids)])

        if search_views:
            import ipdb; ipdb.set_trace()
            # TODO Manage this exception (create as many ActWindow as there are remaining search views)
            # raise UserError('Some search views have not been linked to Window Actions!')

        # Add sub menu items
        sub_menus = self._create_menu_items(other_action_windows + new_action_windows)
        # sub_menus = Menu
        # for seq, act_window in enumerate(other_action_windows + new_action_windows):
        #     sub_menus |= Menu.create({
        #         'name': '%s %s (%s)'.format(
        #             '[NEW]' if act_window.created_for_migration else '',
        #             act_window.name,
        #             act_window.view_mode),
        #         'parent_id': self.root_menu_item_id.id,
        #         'action': 'ir.actions.act_window,%d' % (act_window.id,),
        #         'sequence': seq,
        #     })


        # invitation_template = self.env.ref('sport_club_manager.email_template_membership_affiliation_invitation')
        # ctx = {
        #     'company_id': self.env.user.company_id,
        #     'dbname': self._cr.dbname,
        # }
        # for membership in self:
        #     if membership.state not in ('requested', 'member', 'rejected'):
        #         invitation_template.with_context(ctx).send_mail(membership.id)
        #         membership.invitation_mail_sent = True

        # self.write({
        #     # 'sub_menu_item_ids': [(4, rec.id) for rec in sub_menus],
        #     'action_window_views_ids': [(4, rec.id) for rec in new_action_window_views],
        #     'action_window_ids': [(4, rec.id) for rec in new_action_windows],
        # })


        return {
            'type': 'ir.actions.client',
            'tag': 'reload',  # TODO Does not reload!
        }
        # return {'type': 'ir.actions.act_window_close'}  # TODO Reload page here...


    def _create_menu_items(self, act_windows):
        Menu = self.env['ir.ui.menu']

        if not self.root_menu_item_id.id:
            raise UserError('No root Menu Item for module %s has been created!' % self.module_id.name)


        menus = []
        parent_menu_items = self.sub_menu_item_ids
        for seq, act_window in enumerate(act_windows):


            # parent_menu_item = Menu.search([
            #     ('module_name', '=', self.module_id.name),
            #     ('model_name', '=', act_window.res_model)
            # ])
            parent_menu_item = parent_menu_items.filtered(lambda mi: mi.model_name == act_window.res_model)
            if not parent_menu_item:
                parent_menu_item = Menu.create({
                    'name': act_window.res_model,
                    'parent_id': self.root_menu_item_id.id,
                    # 'sequence': seq * 10,
                    'module_name': self.module_id.name,
                    'model_name': act_window.res_model,
                    'migration_module_view_id': self.id,
                })
                parent_menu_items |= parent_menu_item

            menus.append({
                'name': '{} {} ({})'.format(
                    '[NEW]' if act_window.created_for_migration else '',
                    act_window.name,
                    act_window.view_mode),
                'parent_id': parent_menu_item.id,
                'action': 'ir.actions.act_window,%d' % (act_window.id,),
                'sequence': seq * 10,
                'migration_module_view_id': self.id,
            })
        Menu.create(menus)


# return Menu.create([{
#         'name': '{} {} ({})'.format(
#             '[NEW]' if act_window.created_for_migration else '',
#             act_window.name,
#             act_window.view_mode),
#         'parent_id': self.root_menu_item_id.id,
#         'action': 'ir.actions.act_window,%d' % (act_window.id,),
#         'sequence': seq * 10,
#         'migration_module_view_id': self.id,
#     } for seq, act_window in enumerate(act_windows)
# ])



# TODO Add a delete button and delete all o2m fields (+ main menu item)


# Example in ir_module.py:
# @api.depends('name', 'state')
# def _get_views(self):
#     IrModelData = self.env['ir.model.data'].with_context(active_test=True)
#     dmodels = ['ir.ui.view', 'ir.actions.report', 'ir.ui.menu']

#     for module in self:
#         # Skip uninstalled modules below, no data to find anyway.
#         if module.state not in ('installed', 'to upgrade', 'to remove'):
#             module.views_by_module = ""
#             module.reports_by_module = ""
#             module.menus_by_module = ""
#             continue

#         # then, search and group ir.model.data records
#         imd_models = defaultdict(list)
#         imd_domain = [('module', '=', module.name), ('model', 'in', tuple(dmodels))]
#         for data in IrModelData.sudo().search(imd_domain):
#             imd_models[data.model].append(data.res_id)

#         def browse(model):
#             # as this method is called before the module update, some xmlid
#             # may be invalid at this stage; explictly filter records before
#             # reading them
#             return self.env[model].browse(imd_models[model]).exists()

#         def format_view(v):
#             return '%s%s (%s)' % (v.inherit_id and '* INHERIT ' or '', v.name, v.type)

#         module.views_by_module = "\n".join(sorted(format_view(v) for v in browse('ir.ui.view')))
#         module.reports_by_module = "\n".join(sorted(r.name for r in browse('ir.actions.report')))
#         module.menus_by_module = "\n".join(sorted(m.complete_name for m in browse('ir.ui.menu')))


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    migration_module_view_id = fields.Many2one('migration_module_views', string='Module Views')
    module_name = fields.Char('Module Name')
    model_name = fields.Char('Model Name')


class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    migration_module_view_id = fields.Many2one('migration_module_views', string='Module Views')


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    migration_module_view_id = fields.Many2one('migration_module_views', string='Module Views')
    created_for_migration = fields.Boolean(string='Created for Migration')
