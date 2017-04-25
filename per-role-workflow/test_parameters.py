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

        action = parameters.GetProfileNameAction('oooq_compute')
        result = action.run()
        expected_result = "compute"
        self.assertEqual(result,expected_result)

