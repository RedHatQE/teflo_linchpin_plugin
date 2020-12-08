# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Red Hat, Inc.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
    Pykwalify extensions module.

    Module containing custom validation functions used for schema checking.

    :copyright: (c) 2020 Red Hat, Inc.
    :license: GPLv3, see LICENSE for more details.
"""


def valid_combos(value, rule_obj, path):

    meg1 = set(['pinfile', 'topology'])
    meg2 = set(['resource_group_type', 'resource_definitions'])

    # Assume they are using the old provider method
    if len(value) == 0:
        return True

    # pinf
    if len(meg1.intersection(value.keys())) > 1 or \
            (len(meg1.intersection(value.keys())) > 0 and len(meg2.intersection(value.keys())) > 0):
        raise AssertionError(
            'The pinfile, topology, and/or resource keys have been specified together. Can only use one at a time.'
        )

    if len(meg1.intersection(value.keys())) == 0 and len(meg2.intersection(value.keys())) < 2:
        raise AssertionError(
            'Either missing resource_group_type or resource_definitions. They must be used together.'
        )

    if 'template_data' in value and len(meg1.intersection(value.keys())) == 0:
        raise AssertionError(
            'The key, template_data, should only be used with Linchpin files like PinFiles, topology files, etc.'
        )

    if 'credentials' in value and len(meg1.intersection(value.keys())) != 0:
        raise AssertionError(
            'The key, credentials, should only be used with resource_group_type and resource_definitions.'
        )

    return True
