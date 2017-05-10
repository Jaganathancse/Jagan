# Copyright 2017 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import mock

from tripleo_common.actions import derive_parameters
from tripleo_common.tests import base


class GetProfileNameActionTest(base.TestCase):

    @mock.patch('tripleo_common.utils.parameters.get_profile_name')
    @mock.patch('tripleo_common.actions.base.TripleOAction.'
                'get_compute_client')
    @mock.patch('mistral.context.ctx')
    def test_run(self, mock_ctx, mock_get_compute_client,
                 mock_get_profile_name):
        mock_ctx.return_value = mock.MagicMock()

        params = {'capabilities:profile': 'compute'}
        mock_get_profile_name.return_value = params['capabilities:profile']

        action = derive_parameters.GetProfileNameAction('oooq_compute')
        result = action.run()
        expected_result = "compute"
        self.assertEqual(result, expected_result)
