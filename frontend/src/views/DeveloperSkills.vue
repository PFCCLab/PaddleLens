<template>

  <div class="container-fluid text-dark text-center py-4 mb-2">
    <h2>开发者能力度量</h2>
  </div>

  <div class="container-fluid py-2 mb-3 w-50">
    <div class="row align-items-center g-2">
      <div class="col-auto">
        <label for="githubUser" class="col-form-label">请输入 GitHub 用户名：</label>
      </div>
      <div class="col">
        <div class="input-group">
          <input
            v-model="githubUser"
            @keyup.enter="analyzeSkills"
            id="githubUser"
            class="form-control shadow-none"
            placeholder="例如 torvalds"
          />
          <button @click="analyzeSkills" class="btn btn-light border">分析</button>
        </div>
      </div>
    </div>
  </div>

  <div class="container-fluid py-2 mb-5 w-75">
    
    <div v-if="loading" class="text-center">分析中，请稍后...</div>

    <div v-if="result">
      <h3 class="text-center border-top mb-3 py-3 my-3">{{ result.username }}的能力度量结果</h3>

      <p class="text-secondary text-center">数据最后更新：{{ result.date }}</p>

      <!-- 基本信息 -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">基本信息</h5>
      <div class="row mb-3">
        <div class="col-md-3 mb-2">
          <label class="form-label"><strong>用户名</strong></label>
          <div>{{ result.basic_info.username || '无' }}</div>
        </div>
        <div class="col-md-3 mb-2">
          <label class="form-label"><strong>昵称</strong></label>
          <div>{{ result.basic_info.name || '无' }}</div>
        </div>
        <div class="col-md-3 mb-2">
          <label class="form-label"><strong>邮箱</strong></label>
          <div>{{ result.basic_info.email || '无' }}</div>
        </div>
        <div class="col-md-3 mb-2">
          <label class="form-label"><strong>公司</strong></label>
          <div>{{ result.basic_info.company || '无' }}</div>
        </div>

        <div class="col-md-3 mb-2">
          <label class="form-label"><strong>位置</strong></label>
          <div>{{ result.basic_info.location || '无' }}</div>
        </div>
        <div class="col-md-3 mb-2">
          <label class="form-label"><strong>创建日期</strong></label>
          <div>{{ result.basic_info.created_at || '无' }}</div>
        </div>
        <div class="col-md-3 mb-2">
          <label class="form-label"><strong>关注数量</strong></label>
          <div>{{ result.basic_info.following || 0 }}</div>
        </div>
        <div class="col-md-3 mb-2">
          <label class="form-label"><strong>粉丝数量</strong></label>
          <div>{{ result.basic_info.followers || 0 }}</div>
        </div>
      </div>

      <!-- 开发经验 -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">在飞桨中的开发经验</h5>
      <div class="container-fluid border-bottom">
        <div class="row">
          <div class="col-md-4 mb-2">
            <p><strong>Repos：</strong>{{ result.experience.data.paddle_repos_cnt || 0 }}</p>
          </div>
          <div class="col-md-4 mb-2">
            <p><strong>Commits：</strong>{{ result.experience.data.commits_cnt || 0 }}</p>
          </div>
          <div class="col-md-4 mb-2">
            <p><strong>PRs：</strong>{{ result.experience.data.prs_cnt || 0 }}</p>
          </div>

          <div class="col-md-4 mb-2">
            <p><strong>Issues：</strong>{{ result.experience.data.issues_cnt || 0 }}</p>
          </div>
          <div class="col-md-4 mb-2">
            <p><strong>Comments：</strong>{{ result.experience.data.comments_cnt || 0 }}</p>
          </div>
          <div class="col-md-4 mb-2">
            <p><strong>Reviews：</strong>{{ result.experience.data.reviews_cnt || 0 }}</p>
          </div>
        </div>
      </div>

      <div class="container-fluid border-bottom py-3 my-3">
        <h6 class="mb-3">>在飞桨的Merge权限</h6>
        <div class=""> 拥有merge权限的仓库数: {{ result.experience.data.repos_can_merge_cnt || 0 }}，分别为：</div>
        <ul>
          <li v-for="repo in result.experience.data.repos_can_merge" :key="repo">{{ repo }}</li>
        </ul>
      </div>

      <div class="container-fluid border-bottom py-3 my-3">
        <h6 class="mb-3"> >贡献数量Top 5的项目</h6>
        <div class="img-fluid d-block mx-auto" ref="plot_fig_repo_contrib" style="width: 100%; height: 80%;"></div>
      </div>

      <div class="container-fluid py-3 my-3">
        <h6 class="mb-3"> >最近一年的贡献</h6>
        <div class="img-fluid d-block mx-auto" ref="plot_fig_recent_contrib" style="width: 100%; height: 80%;"></div>
      </div>

      <!-- 硬技能 -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">硬技能</h5>
      <div class="m-2 indent-text">
        <small class="text-muted">硬技能是解决具体软件开发问题时所需要的具体的技术技能和知识，这些技能和知识能够在软件开发过程中直接运用。</small>
      </div>
      <div class="container-fluid border-bottom py-3 my-3">
        <h6 class="mb-3"> >编程语言使用能力 </h6>
        <div class="m-2 indent-text">
          <small class="text-muted">衡量开发者掌握和使用语言工具的广度和深度。使用遗忘曲线加权后的修改文件后缀名数量度量。</small>
        </div>
        <div ref="plot_fig_lang" style="width: 100%; height: 80%;"></div>
      </div>
      <div class="container-fluid border-bottom py-3 my-3">
        <h6 class="mb-3"> >领域能力 </h6>
        <div class="m-2 indent-text">
          <small class="text-muted">衡量开发者在深度学习各子领域（如 cv、nlp 等）中所具备的技术理解与实践的能力。根据所参与所有项目的类型来度量，项目类型由项目标签和大语言模型对Readme进行的类型判断共同决定。</small>
        </div>
        <img :src="'data:image/png;base64,' + result.hardskill.fig_domain_bytes" class="img-fluid d-block mx-auto" alt="领域能力图" style="width: 500px;" />
      </div>

      <div class="container-fluid py-3 my-3">
        <h6 class="mb-3"> >问题解决能力 </h6>
        <div class="m-2 indent-text">
          <small class="text-muted">衡量开发者在真实开发任务中的技术水平、编程效率以及解决实际问题的能力。使用项目难度、贡献重要度和任务类型组合度量。</small>
        </div>
        <div ref="plot_fig_solving" class="img-fluid d-block mx-auto" style="width: 100%; height: 80%;"></div>
      </div>

      <!-- 软技能 -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">软技能</h5>
      <div class="m-2 indent-text">
        <small class="text-muted">软技能是影响开发者开发效率、任务协调效果、团队协作水平等方面的非技术性能力，尽管这类能力并不直接参与代码实现，但其表现往往对软件开发过程的稳定性、交付质量和项目成功起到关键作用。</small>
      </div>
      <div class="container-fluid border-bottom py-3 my-3">
        <h6 class="mb-3"> >责任心 </h6>
        <div class="m-2 indent-text">
          <small class="text-muted">长时间持续参与某个项目被视为有责任心的表现，因此衡量参与的持续性和积极性。持续性通过在过去一年内的活跃月数和最大连续贡献月数来度量；积极性使用在使用所有半年窗口的平均活跃月数度量。</small>
        </div>
        <div class="row mb-3">
          <div class="col-md-6 mb-2">
            <div ref="plot_fig_consistency" class="img-fluid d-block mx-auto" style="width: 100%; height: 50%;"></div>
          </div>
          <div class="col-md-6 mb-2">
            <div ref="plot_fig_activeness" class="img-fluid d-block mx-auto" style="width: 100%; height: 50%;"></div>
          </div>
        </div>
      </div>

      <div class="container-fluid border-bottom py-3 my-3">
        <h6 class="mb-3"> >时间管理能力 </h6>
        <div class="m-2 indent-text">
          <small class="text-muted">衡量开发者在一段时间内同时为多个项目做出贡献的能力。使用在两个月内的最多月月项目数量度量。</small>
        </div>
        <div class="mt-3 indent-text">
          在 {{ result.softskill.time_mgmt.max_active_month_start || "-" }} 到 {{ result.softskill.time_mgmt.max_active_month_end
            || "-" }} 两个月内，总共在{{ result.softskill.time_mgmt.active_projects.length || 0 }}个项目中贡献了
          {{ result.softskill.time_mgmt.commit_count || 0 }}个commit。这些项目分别是
          <ul>
            <li v-for="repo in result.softskill.time_mgmt.active_projects" :key="repo">{{ repo }}</li>
          </ul>
        </div>
      </div>

      <div class="container-fluid py-3 my-3">
        <h6> 沟通能力 </h6>
        <div class="m-2 indent-text">
          <small class="text-muted">衡量开发者在项目中的沟通与协作能力，使用开发者的 Commit message 的有信息量程度作为其沟通能力的外在表现之一。一个“好”的提交信息通常应清晰说明：What，即该提交做了什么具体更改，例如修复了哪个问题、增加了哪个功能；Why，即该提交的动机或目标，例如修复是为何必要，引入新特性的背景考虑等。</small>
        </div>
        <div class="mt-3 indent-text">沟通能力总分为 {{ result.softskill.comm_score || 0 }} (满分100)。不同类型的提交信息示例：</div>
        <div class="mt-3 indent-text">
          <ul v-if="result?.softskill?.sample_commits">
            <li v-if="result.softskill.sample_commits['what+why']">
              <span>What + Why（优秀）</span>：
              <a
                :href="commitLink(result.softskill.sample_commits['what+why'])"
                target="_blank"
              >查看提交</a>
            </li>
            <li v-if="result.softskill.sample_commits['what']">
              <span>What（只说做了什么）</span>：
              <a
                :href="commitLink(result.softskill.sample_commits['what'])"
                target="_blank"
              >查看提交</a>
            </li>
            <li v-if="result.softskill.sample_commits['why']">
              <span>Why（只说为何要改）</span>：
              <a
                :href="commitLink(result.softskill.sample_commits['why'])"
                target="_blank"
              >查看提交</a>
            </li>
            <li v-if="result.softskill.sample_commits['other']">
              <span>Other（未提供有效信息）</span>：
              <a
                :href="commitLink(result.softskill.sample_commits['other'])"
                target="_blank"
              >查看提交</a>
            </li>
            <li v-if="Object.keys(result.softskill.sample_commits).length === 0">
              无提交
            </li>
          </ul>
        </div>
        <div ref="plot_fig_comm" style="width: 100%; height: 80%;"></div>
      </div>

    </div>
  </div>

</template>

<script setup>
import { ref, nextTick } from 'vue'
import axios from 'axios'
import Plotly from 'plotly.js-dist-min'

//创建响应式数据
// 变量
const githubUser = ref('')
const date = ref('')
const result = ref(null)
const loading = ref(false)
// 引用 DOM 容器
const plot_fig_repo_contrib = ref(null)
const plot_fig_recent_contrib = ref(null)
const plot_fig_lang = ref(null)
const plot_fig_solving = ref(null)
const plot_fig_consistency = ref(null)
const plot_fig_activeness = ref(null)
const plot_fig_comm = ref(null)

async function analyzeSkills() {
  if (!githubUser.value.trim()) {
    alert('请输入用户');
    return;
  }

  result.value = null
  loading.value = true

  try {
    const API_BASE = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, ''); // 去掉末尾/
    const res = await axios.post(`${API_BASE}/dvpr_skills/`, {
      github_user: githubUser.value
    })
    result.value = res.data
    date.value = result.value.date


    // 解构数据
    const r = result.value

    const plot_fig_repo_contrib_Data = r.experience?.fig_repo_contrib?.data || []
    const plot_fig_repo_contrib_Layout = r.experience?.fig_repo_contrib?.layout || {}

    const plot_fig_recent_contrib_Data = r.experience?.fig_recent_contrib?.data || []
    const plot_fig_recent_contrib_Layout = r.experience?.fig_recent_contrib?.layout || {}

    const plot_fig_lang_Data = r.hardskill?.fig_lang?.data || []
    const plot_fig_lang_Layout = r.hardskill?.fig_lang?.layout || {}

    const plot_fig_solving_Data = r.hardskill?.fig_solving?.data || []
    const plot_fig_solving_Layout = r.hardskill?.fig_solving?.layout || {}

    const plot_fig_consistency_Data = r.softskill?.fig_consistency?.data || []
    const plot_fig_consistency_Layout = r.softskill?.fig_consistency?.layout || {}

    const plot_fig_activeness_Data = r.softskill?.fig_activeness?.data || []
    const plot_fig_activeness_Layout = r.softskill?.fig_activeness?.layout || {}

    const plot_fig_comm_Data = r.softskill?.fig_comm?.data || []
    const plot_fig_comm_Layout = r.softskill?.fig_comm?.layout || {}

    // 等待 DOM 完成更新，再开始渲染图
    await nextTick()

    Plotly.newPlot(plot_fig_repo_contrib.value, plot_fig_repo_contrib_Data, plot_fig_repo_contrib_Layout)
    Plotly.newPlot(plot_fig_recent_contrib.value, plot_fig_recent_contrib_Data, plot_fig_recent_contrib_Layout)
    Plotly.newPlot(plot_fig_lang.value, plot_fig_lang_Data, plot_fig_lang_Layout)
    Plotly.newPlot(plot_fig_solving.value, plot_fig_solving_Data, plot_fig_solving_Layout)
    Plotly.newPlot(plot_fig_consistency.value, plot_fig_consistency_Data, plot_fig_consistency_Layout)
    Plotly.newPlot(plot_fig_activeness.value, plot_fig_activeness_Data, plot_fig_activeness_Layout)
    Plotly.newPlot(plot_fig_comm.value, plot_fig_comm_Data, plot_fig_comm_Layout)

  } catch (err) {
    if (err.response && err.response.data && err.response.data.detail) {
      alert('分析失败：' + err.response.data.detail)
    } else if (axios.isCancel(err)) {
      alert('请求被取消')
    } else if (err.message.includes('timeout')) {
      alert('请求超时，请稍后再试')
    } else {
      alert('分析失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

function commitLink(commit) {
  return `https://github.com/${commit.repo}/commit/${commit.sha}`
}
</script>

<style scoped>
.indent-text {
  text-indent: 2em;
  text-align: justify; /* 可选：让段落看起来左右对齐更像 Word */
}
</style>