    def test_goal_detail_and_progress(self):

        self.assertContains(response, '50<span class="text-xl text-slate-400">%</span>', html=True)
