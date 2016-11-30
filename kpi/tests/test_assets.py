#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
from collections import OrderedDict

from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase

from kpi.models import Asset
from kpi.models import Collection
from kpi.models.object_permission import get_all_objects_for_user

# move this into a fixture file?
# note: this is not a very robust example of a cascading select
CASCADE_CONTENT = {u'survey': [{u'type': u'select_one',
                                u'select_from_list_name': u'country',
                                u'label': [u'country'],
                                u'required': True},
                               {u'type': u'select_one',
                                u'select_from_list_name': u'region',
                                u'label': [u'region'],
                                u'choice_filter': u'country=${country}',
                                u'required': True},
                               {u'type': u'select_one',
                                u'select_from_list_name': u'town',
                                u'label': [u'region'],
                                u'choice_filter': u'region=${region}',
                                u'required': True}],
                   u'choices': [{u'label': [u'France'],
                                 u'list_name': u'country',
                                 u'name': u'france'},
                                {u'country': u'france',
                                 u'label': [u'\xcele-de-France'],
                                 u'list_name': u'region',
                                 u'name': u'ile-de-france'},
                                {u'region': u'ile-de-france',
                                 u'label': [u'Paris'],
                                 u'list_name': u'town',
                                 u'name': u'paris'}],
                   u'translated': [u'label'],
                   u'translations': [None]}


class AssetsTestCase(TestCase):
    fixtures = ['test_data']

    def setUp(self):
        self.user = User.objects.all()[0]
        self.asset = Asset.objects.create(content={'survey': [
            {u'type': u'text',
             u'label': u'Question 1',
             u'name': u'q1',
             u'$kuid': u'abc'},
            {u'type': u'text',
             u'label': u'Question 2',
             u'name': u'q2',
             u'$kuid': u'def'},
        ]}, owner=self.user, asset_type='survey')
        self.sa = self.asset


class CreateAssetVersions(AssetsTestCase):

    def test_asset_with_versions(self):
        self.asset.content['survey'][0]['type'] = 'integer'
        self.assertEqual(self.asset.content['survey'][0]['type'], 'integer')
        self.asset.save()
        self.assertEqual(self.asset.asset_versions.count(), 2)

    def test_asset_can_be_owned(self):
        self.assertEqual(self.asset.owner, self.user)

    def test_asset_can_be_tagged(self):
        def _list_tag_names():
            return sorted(list(self.asset.tags.names()))
        self.assertEqual(_list_tag_names(), [])
        self.asset.tags.add('tag1')
        self.assertEqual(_list_tag_names(), ['tag1'])
        # duplicate tags ignored
        self.asset.tags.add('tag1')
        self.assertEqual(_list_tag_names(), ['tag1'])
        self.asset.tags.add('tag2')
        self.assertEqual(_list_tag_names(), ['tag1', 'tag2'])

    def test_asset_can_be_anonymous(self):
        anon_asset = Asset.objects.create(content=self.asset.content)
        self.assertEqual(anon_asset.owner, None)


class AssetContentTests(AssetsTestCase):
    def _wrap_field(self, field_name, value):
        return {'survey': [
            {'type': 'text', 'name': 'x'},
            {'type': 'text', 'name': 'y', field_name: value},
        ]}

    def _wrap_type(self, type_val, select_from=None):
        r1 = {'type': type_val,
              'name': 'q_yn',
              'label': 'Yes or No'}
        if select_from:
            r1['select_from_list_name'] = select_from
        return {'survey': [r1], 'choices': [
            {'list_name': 'yn', 'name': 'y', 'label': 'Yes'},
            {'list_name': 'yn', 'name': 'n', 'label': 'No'},
        ]}

    def test_rename_null_translation(self):
        '''
        This allows a workaround to enable multi-translation editing in the
        form builder which focuses on the "null" language.
        '''
        self.asset = Asset.objects.create(content={'survey': [
            {'label': ['lang1', 'lang2'], 'type': 'text', 'name': 'q1'},
        ],
            'translations': ['lang1', None],
            '#null_translation': 'lang2',
        })
        self.assertEqual(self.asset.content['translations'], ['lang1', 'lang2'])
        self.assertTrue('#null_translation' not in self.asset.content)

    def test_rename_translation(self):
        '''
        This allows a workaround to enable multi-translation editing in the
        form builder which focuses on the "null" language.
        '''
        self.asset = Asset.objects.create(content={'survey': [
            {'label': ['lang1', 'lang2'], 'type': 'text', 'name': 'q1'},
        ],
            'translations': ['lang1', None],
        })
        self.asset.rename_translation(None, 'lang2')
        self.assertEqual(self.asset.content['translations'], ['lang1', 'lang2'])

    def test_rename_translation_fail(self):
        '''
        This allows a workaround to enable multi-translation editing in the
        form builder which focuses on the "null" language.
        '''
        self.asset = Asset.objects.create(content={'survey': [
            {'label': ['lang1', 'lang2'], 'type': 'text', 'name': 'q1'},
        ],
            'translations': ['lang1', None],
        })
        try:
            self.asset.rename_translation('lang1', None)
            # shouldnt get here
            self.fail()
        except:
            self.assertEqual(self.asset.content.get('translations'), ['lang1', None])

    def test_flatten_empty_relevant(self):
        content = self._wrap_field('relevant', [])
        a1 = Asset.objects.create(content=content, asset_type='survey')
        ss_struct = a1.to_ss_structure()['survey']
        self.assertEqual(ss_struct[1]['relevant'], '')

    def test_flatten_relevant(self):
        content = self._wrap_field('relevant', [{'@lookup': 'x'}])
        a1 = Asset.objects.create(content=content, asset_type='survey')
        ss_struct = a1.to_ss_structure()['survey']
        self.assertEqual(ss_struct[1]['relevant'], '${x}')

    def test_flatten_constraints(self):
        content = self._wrap_field('constraint', ['.', '>', {'@lookup': 'x'}])
        a1 = Asset.objects.create(content=content, asset_type='survey')
        ss_struct = a1.to_ss_structure()['survey']
        self.assertEqual(ss_struct[1]['constraint'], '. > ${x}')

    def test_flatten_select_one_type(self):
        content = self._wrap_type('select_one', select_from='yn')
        a1 = Asset.objects.create(content=content, asset_type='survey')
        ss_struct = a1.to_ss_structure()['survey']
        self.assertEqual(ss_struct[0]['type'], 'select_one yn')

    def test_flatten_select_multiple_type(self):
        content = self._wrap_type('select_multiple', select_from='yn')
        a1 = Asset.objects.create(content=content, asset_type='survey')
        ss_struct = a1.to_ss_structure()['survey']
        self.assertEqual(ss_struct[0]['type'], 'select_multiple yn')

    def test_expand_content(self):
        content = {'survey': [{'type': 'select_one abc'}]}
        a1 = Asset.objects.create(content=content, asset_type='survey')
        r1 = a1.content.get('survey')[0]
        self.assertEqual(r1['type'], 'select_one')
        self.assertEqual(r1['select_from_list_name'], 'abc')

    def test_get_standardized_content(self):
        def _asset_with_content(_c):
            asset = Asset.objects.create(asset_type='survey', content=_c)
            return asset.ordered_xlsform_content()
        x1 = _asset_with_content({
            'survey': [
                {'type': 'text', 'label': '_asset_with_content'}
            ]
        })
        self.assertTrue(None not in [x.get('name')
                                     for x in x1['survey']])

    def test_convert_content_to_ordered_dicts(self):
        _c = self.asset.ordered_xlsform_content(
            append={
                'survey': [
                    {'type': 'note', 'label': ['wee'
                     for _ in self.asset.content.get('translations')]
                     },
                ],
                'settings': {
                    'asdf': 'jkl',
                }
            },
        )
        self.assertTrue(isinstance(_c, OrderedDict))
        self.assertTrue(_c.keys(), ['survey', 'settings'])
        self.assertTrue(isinstance(_c['survey'][0], OrderedDict))
        self.assertEqual(_c['settings'][0]['asdf'], 'jkl')
        self.assertEqual(_c['survey'][-1]['type'], 'note')


class AssetSettingsTests(AssetsTestCase):
    def _content(self, form_title='some form title'):
        return {
            'survey': [
                {'type': 'text', 'label': 'Question 1',
                 'name': 'q1', 'kuid': 'abc'},
                {'type': 'text', 'label': 'Question 2',
                 'name': 'q2', 'kuid': 'def'}
            ],
            # settingslist
            'settings': [
                {'form_title': form_title,
                 'id_string': 'xid_stringx'},
            ]
        }

    def test_asset_type_changes_based_on_row_count(self):
        # we are inferring the asset_type from the content so that
        # a question can become a block and vice versa
        a1 = Asset.objects.create(content=self._content(), owner=self.user,
                                  asset_type='block')
        self.assertEqual(a1.asset_type, 'block')
        self.assertEqual(len(a1.content['survey']), 2)

        # shorten the content
        a1.content['survey'] = [a1.content['survey'][0]]

        # trigger the asset_type change
        a1.save()
        self.assertEqual(a1.asset_type, 'question')
        self.assertEqual(len(a1.content['survey']), 1)

    def test_blocks_strip_settings(self):
        a1 = Asset.objects.create(content=self._content(), owner=self.user,
                                  asset_type='block')
        self.assertEqual(a1.content['settings'], {})

    def test_questions_strip_settings(self):
        a1 = Asset.objects.create(content=self._content(), owner=self.user,
                                  asset_type='question')
        self.assertEqual(a1.content['settings'], {})

    def test_surveys_retain_settings(self):
        _content = self._content()
        _content['settings'] = {
            'style': 'pages',
        }
        a1 = Asset.objects.create(content=_content, owner=self.user,
                                  asset_type='survey')
        self.assertEqual(a1.asset_type, 'survey')
        self.assertTrue('settings' in a1.content)
        self.assertEqual(a1.content['settings'].get('style'), 'pages')

    def test_surveys_move_form_title_to_name(self):
        a1 = Asset.objects.create(content=self._content('abcxyz'),
                                  owner=self.user,
                                  asset_type='survey')
        # settingslist
        settings = a1.content['settings']
        self.assertEqual(a1.asset_type, 'survey')
        self.assertTrue('form_title' not in settings)
        self.assertEqual(a1.name, 'abcxyz')



class AssetScoreTestCase(TestCase):
    fixtures = ['test_data']

    def test_score_can_be_exported(self):
        _matrix_score = {
            u'survey': [
                {u'kobo--score-choices': u'nb7ud55',
                 u'label': [u'Los Angeles'],
                 u'required': True,
                 u'type': u'begin_score'},
                {u'label': [u'Food'], u'type': u'score__row'},
                {u'label': [u'Music'], u'type': u'score__row'},
                {u'label': [u'Night life'], u'type': u'score__row'},
                {u'label': [u'Housing'], u'type': u'score__row'},
                {u'label': [u'Culture'], u'type': u'score__row'},
                {u'type': u'end_score'}],
            u'choices': [
                {u'label': [u'Great'],
                 u'list_name': u'nb7ud55'},
                {u'label': [u'OK'],
                 u'list_name': u'nb7ud55'},
                {u'label': [u'Bad'],
                 u'list_name': u'nb7ud55'}],
            u'settings': {},
        }
        a1 = Asset.objects.create(content=_matrix_score, asset_type='survey')
        _snapshot = a1.snapshot
        self.assertNotEqual(_snapshot.xml, '')
        self.assertNotEqual(_snapshot.details['status'], 'failure')


class AssetSnapshotXmlTestCase(AssetSettingsTests):
    def test_cascading_select_xform(self):
        asset = Asset.objects.create(asset_type='survey',
                                     content=CASCADE_CONTENT)
        # kuids automatically populated by asset.save()
        survey_kuids = [row.get('$kuid') for row in asset.content.get('survey')]
        choices_kuids = [row.get('$kuid') for row in asset.content.get('choices')]
        self.assertTrue(None not in survey_kuids)
        self.assertTrue(None not in choices_kuids)
        # asset.snapshot.xml generates a document that does not have any
        # "$kuid" or "<$kuid>x</$kuid>" elements
        _xml = asset.snapshot.xml

        # as is in every xform:
        self.assertTrue('<instance>' in _xml)
        # specific to this cascading select form:
        self.assertTrue('<instance id="town">' in _xml)
        self.assertTrue('<instance id="region">' in _xml)
        self.assertTrue('<instance id="country">' in _xml)

        self.assertTrue('$kuid' not in _xml)

    def test_surveys_exported_to_xml_have_id_string_and_title(self):
        a1 = Asset.objects.create(content=self._content('abcxyz'),
                                  owner=self.user,
                                  asset_type='survey')
        export = a1.snapshot
        self.assertTrue('<h:title>abcxyz</h:title>' in export.xml)
        self.assertTrue('<data id="xid_stringx">' in export.xml)


# TODO: test values of "valid_xlsform_content"

# class ReadAssetsTests(AssetsTestCase):
#     def test_strip_kuids(self):
#         sans_kuid = self.sa.to_ss_structure(content_tag='survey', strip_kuids=True)['survey']
#         self.assertEqual(len(sans_kuid), 2)
#         self.assertTrue('kuid' not in sans_kuid[0].keys())

# class UpdateAssetsTest(AssetsTestCase):
#     def test_add_settings(self):
#         self.assertEqual(self.asset.settings, None)
#         self.asset.settings = {'style':'grid-theme'}
# self.assertEqual(self.asset.settings, {'style':'grid-theme'})
#         ss_struct = self.asset.to_ss_structure()['settings']
#         self.assertEqual(len(ss_struct), 1)
#         self.assertEqual(ss_struct[0], {
#                 'style': 'grid-theme',
#             })

class ShareAssetsTest(AssetsTestCase):

    def setUp(self):
        super(ShareAssetsTest, self).setUp()
        self.someuser = User.objects.get(username='someuser')
        self.anotheruser = User.objects.get(username='anotheruser')
        self.coll = Collection.objects.create(owner=self.user)
        # Make a copy of self.asset and put it inside self.coll
        self.asset_in_coll = self.asset
        self.asset_in_coll.pk = None
        self.asset_in_coll.uid = ''
        self.asset_in_coll.parent = self.coll
        self.asset_in_coll.save()

    def grant_and_revoke_standalone(self, user, perm):
        self.assertEqual(user.has_perm(perm, self.asset), False)
        # Grant
        self.asset.assign_perm(user, perm)
        self.assertEqual(user.has_perm(perm, self.asset), True)
        # Revoke
        self.asset.remove_perm(user, perm)
        self.assertEqual(user.has_perm(perm, self.asset), False)

    def test_user_view_permission(self):
        self.grant_and_revoke_standalone(self.someuser, 'view_asset')

    def test_user_change_permission(self):
        self.grant_and_revoke_standalone(self.someuser, 'change_asset')

    def grant_and_revoke_parent(self, user, perm):
        # Collection permissions have different suffixes
        coll_perm = re.sub('_asset$', '_collection', perm)
        self.assertEqual(user.has_perm(perm, self.asset_in_coll), False)
        # Grant
        self.coll.assign_perm(user, coll_perm)
        self.assertEqual(user.has_perm(perm, self.asset_in_coll), True)
        # Revoke
        self.coll.remove_perm(user, coll_perm)
        self.assertEqual(user.has_perm(perm, self.asset_in_coll), False)

    def test_user_inherited_view_permission(self):
        self.grant_and_revoke_parent(self.someuser, 'view_asset')

    def test_user_inherited_change_permission(self):
        self.grant_and_revoke_parent(self.someuser, 'change_asset')

    def assign_collection_asset_perms(self, user, collection_perm, asset_perm,
                                      collection_deny=False, asset_deny=False,
                                      asset_first=False):
        self.assertEqual(user.has_perm(collection_perm, self.coll), False)
        self.assertEqual(user.has_perm(asset_perm, self.asset_in_coll), False)
        if asset_first:
            self.asset_in_coll.assign_perm(user, asset_perm, deny=asset_deny)
            self.coll.assign_perm(user, collection_perm, deny=collection_deny)
        else:
            self.coll.assign_perm(user, collection_perm, deny=collection_deny)
            self.asset_in_coll.assign_perm(user, asset_perm, deny=asset_deny)
        self.assertEqual(user.has_perm(collection_perm, self.coll),
                         not collection_deny)
        self.assertEqual(user.has_perm(asset_perm, self.asset_in_coll),
                         not asset_deny)

    def test_user_view_collection_change_asset(self, asset_first=False):
        user = self.someuser
        self.assign_collection_asset_perms(
            user,
            'view_collection',
            'change_asset',
            asset_first=asset_first
        )

    def test_user_change_collection_view_asset(self, asset_first=False):
        user = self.someuser
        self.assign_collection_asset_perms(
            user,
            'change_collection',
            'change_asset',
            asset_deny=True,
            asset_first=asset_first
        )
        # assign_collection_asset_perms verifies the assignments, but make sure
        # that the user can still view the asset
        self.assertEqual(user.has_perm('view_asset', self.asset_in_coll),
                         True)

    def test_user_change_collection_deny_asset(self, asset_first=False):
        user = self.someuser
        self.assign_collection_asset_perms(
            user,
            'change_collection',
            'view_asset',
            asset_deny=True,
            asset_first=asset_first
        )
        # Verify that denying view_asset denies change_asset as well
        self.assertEqual(user.has_perm('change_asset',
                                       self.asset_in_coll),
                         False)

    ''' Try the previous tests again, but this time assign permissions to the
    asset before assigning permissions to the collection. '''

    def test_user_change_asset_view_collection(self):
        self.test_user_view_collection_change_asset(asset_first=True)

    def test_user_view_asset_change_collection(self):
        self.test_user_change_collection_view_asset(asset_first=True)

    def test_user_deny_asset_change_collection(self):
        self.test_user_change_collection_deny_asset(asset_first=True)

    def test_query_all_assets_user_can_access(self):
        # The owner should have access to all owned assets
        self.assertEqual(
            get_all_objects_for_user(self.user, Asset).count(),
            2
        )
        # The other user should have nothing yet
        self.assertEqual(
            get_all_objects_for_user(self.someuser, Asset).count(),
            0
        )
        # Grant access and verify the result
        self.asset.assign_perm(self.someuser, 'view_asset')
        self.assertEqual(
            # Without coercion, django.db.models.query.ValuesListQuerySet isn't
            # a real list and will fail the comparison.
            list(
                get_all_objects_for_user(
                    self.someuser,
                    Asset
                ).values_list('pk', flat=True)
            ),
            [self.asset.pk]
        )

    def test_owner_can_edit_permissions(self):
        self.assertTrue(self.asset.owner.has_perm(
            'share_asset',
            self.asset
        ))

    def test_share_asset_permission_is_not_inherited(self):
        # Change self.coll so that its owner isn't a superuser
        self.coll.owner = User.objects.get(username='someuser')
        self.coll.save()
        # Give the child asset a different owner
        self.asset_in_coll.owner = User.objects.get(username='anotheruser')
        # The change permission is inherited; prevent it from allowing
        # users to edit permissions
        self.asset_in_coll.editors_can_change_permissions = False
        self.asset_in_coll.save()
        # Ensure the parent's owner can't change permissions on the child
        self.assertFalse(self.coll.owner.has_perm(
            'share_asset',
            self.asset_in_coll
        ))

    def test_change_permission_provides_share_permission(self):
        someuser = User.objects.get(username='someuser')
        self.assertFalse(someuser.has_perm(
            'change_asset', self.asset))
        # Grant the change permission and make sure it provides
        # share_asset
        self.asset.assign_perm(someuser, 'change_asset')
        self.assertTrue(someuser.has_perm(
            'share_asset', self.asset))
        # Restrict share_asset to the owner and make sure someuser loses
        # the permission
        self.asset.editors_can_change_permissions = False
        self.assertFalse(someuser.has_perm(
            'share_asset', self.asset))

    def test_anonymous_view_permission_on_standalone_asset(self):
        # Grant
        self.assertFalse(AnonymousUser().has_perm(
            'view_asset', self.asset))
        self.asset.assign_perm(AnonymousUser(), 'view_asset')
        self.assertTrue(AnonymousUser().has_perm(
            'view_asset', self.asset))
        # Revoke
        self.asset.remove_perm(AnonymousUser(), 'view_asset')
        self.assertFalse(AnonymousUser().has_perm(
            'view_asset', self.asset))

    def test_anoymous_change_permission_on_standalone_asset(self):
        # TODO: behave properly if ALLOWED_ANONYMOUS_PERMISSIONS actually
        # includes change_asset
        try:
            # This is expected to fail since only real users can have any
            # permissions beyond view
            self.asset.assign_perm(
                AnonymousUser(), 'change_asset')
        except ValidationError:
            pass
        # Make sure the assignment failed
        self.assertFalse(AnonymousUser().has_perm(
            'change_asset', self.asset))

    def test_anonymous_as_baseline_for_authenticated(self):
        ''' If the public can view an object, then all users should be able
        to do the same. '''
        # No one should have any permission yet
        for user_obj in AnonymousUser(), self.someuser:
            self.assertFalse(user_obj.has_perm(
                'view_asset', self.asset))
        # Grant to anonymous
        self.asset.assign_perm(AnonymousUser(), 'view_asset')
        # Check that both anonymous and someuser can view
        for user_obj in AnonymousUser(), self.someuser:
            self.assertTrue(user_obj.has_perm(
                'view_asset', self.asset))
