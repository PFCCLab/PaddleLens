<template>

  <div class="container-fluid text-dark text-center py-4 mb-2">
    <h2>社区健康度度量</h2>
  </div>

  <div class="container-fluid py-2 mb-3 w-50">
    <div class="row align-items-center g-2">
      <div class="col-auto">
        <label for="repo" class="col-form-label">请输入飞桨相关的 GitHub 仓库名：</label>
      </div>
      <div class="col">
        <div class="input-group">
          <input
            v-model="repo"
            @keyup.enter="analyzeHealth"
            id="repo"
            class="form-control shadow-none"
            placeholder="例如 PaddlePaddle/Paddle"
          />
          <button @click="analyzeHealth" class="btn btn-light border">分析</button>
        </div>
      </div>
    </div>
  </div>

  <div class="container-fluid py-2 mb-3 w-75">

    <div v-if="loading" class="text-center">分析中...</div>

    <div v-if="result">
      <h3 class="text-center border-top mb-3 py-3 my-3">社区健康度</h3>

      <div class="m-2 indent-text text-center">
        <p class="text-secondary">最后更新：{{ date }}</p>
        <p class="text-secondary">“最近”指标：最后更新时间的前90天内</p>
        <p class="text-secondary">数据来源：GitHub API & OSS Insight</p>
      </div>

      <!-- vigor -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">项目活力</h5>
      <div class="m-2 indent-text">
        <small class="text-muted">衡量社区的参与程度与活跃度，是判断社区是否“有生命力”的首要指标。</small>
      </div>
      <div class="card shadow-none border-0 border-bottom rounded-0 mb-3"> <!-- development activity -->
        <h5 class="m-4 mb-0">开发活跃度</h5>
        <div class="m-2 indent-text">
          <small class="text-muted">衡量项目中实际开发行为的活跃程度。</small>
        </div>
        <div class="row">
          <!-- 提交数 -->
          <div class="col-md-4">
            <div class="card m-4 border-0" style="background-color: #EBFCD9;">
              <div class="card-body text-center">
                <h5 class="card-title">Commit</h5>
                <!-- <small class="text-muted">代码更新频率和开发节奏</small> -->
                <div class="card-text fs-4 text-dark">{{ vigorCommits.total }}</div>
                <small class="text-muted">最近：{{ vigorCommits.recent }}</small>
              </div>
            </div>
          </div>
          <!-- PR 数 -->
          <div class="col-md-4">
            <div class="card m-4 border-0" style="background-color: #EBFCD9;">
              <div class="card-body text-center">
                <h5 class="card-title">PR</h5>
                <!-- <small class="text-muted">开发者参与度与协作意愿</small> -->
                <div class="card-text fs-4 text-dark">{{ vigorPRs.total }}</div>
                <small class="text-muted">最近：{{ vigorPRs.recent }}</small>
              </div>
            </div>
          </div>
          <!-- 核心开发者review数 -->
          <div class="col-md-4">
            <div class="card m-4 border-0" style="background-color: #EBFCD9;">
              <div class="card-body text-center">
                <h5 class="card-title">Review</h5>
                <!-- <small class="text-muted">代码审查机制的活跃度和规范程</small> -->
                <div class="card-text fs-4 text-dark">{{ vigorReviews.total }}</div>
                <small class="text-muted">最近：{{ vigorReviews.recent }}</small>
              </div>
            </div>
          </div>
        </div>
        <div class="card m-4 mt-0 border-0" style="background-color: #EBFCD9;">
          <div class="card-body text-center">
            <h5 class="card-title">需求完成情况</h5>
            <small class="text-muted">通过带有“feat”等相关标签 issue 的关闭情况，衡量社区响应用户需求的能力</small>
            <div class="row"> <!-- 需求完成比例 -->
              <div class="col-md-6 mb-3">
                <VChart :option="requirementCloseTotalChart" style="height: 220px" autoresize />
              </div>
              <div class="col-md-6 mb-3">
                <VChart :option="requirementCloseRecentChart" style="height: 220px" autoresize />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="row">
        <div class="col-md-8">
          <div class="card shadow-none border-0 border-end rounded-0"> <!-- communication activity -->
            <h5 class="m-4 mb-0">沟通活跃度</h5>
            <div class="m-2 indent-text">
              <small class="text-muted">聚焦于社区成员在协作场景中的交流频率，体现开发过程中团队内部的互动密度与协作意愿。</small>
            </div>
            <div class="row">
              <!-- 评论数卡片 -->
              <div class="col-md-6">
                <div class="card m-4 me-2 border-0" style="background-color: #D9ECFC;">
                  <div class="card-body text-center">
                    <h5 class="card-title">评论</h5>
                    <!-- <small class="text-muted">Issue、PR 的评论数，反应社区内部的交流密度</small> -->
                    <div class="card-text fs-4 text-dark">{{ vigorComments.total || 0 }}</div>
                    <small class="text-muted">最近：{{ vigorComments.recent || 0 }}</small>
                  </div>
                </div>
              </div>
              <!-- Issue 数卡片 -->
              <div class="col-md-6">
                <div class="card m-4 ms-2 border-0" style="background-color: #D9ECFC;">
                  <div class="card-body text-center">
                    <h5 class="card-title">Issue</h5>
                    <!-- <small class="text-muted">衡量用户与开发者之间的问题反馈与功能需求表达的频率</small> -->
                    <div class="card-text fs-4 text-dark">{{ vigorIssues.total || 0 }}</div>
                    <small class="text-muted">最近：{{ vigorIssues.recent || 0 }}</small>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
        </div>
        <div class="col-md-4"> <!-- release activity -->
          <div class="card shadow-none border-0 border-end rounded-0"></div>
            <h5 class="m-4 mb-0">发布活跃度</h5>
            <div class="m-2 indent-text">
              <small class="text-muted">反映社区将开发成果向用户输出的能力。</small>
            </div>
            <div class="row">
              <!-- 提交数 -->
              <div class="col-md-12">
                <div class="card m-4 border-0" style="background-color: #FDF5E6;">
                  <div class="card-body text-center">
                    <h5 class="card-title">Release</h5>
                    <div class="card-text fs-4 text-dark">{{ vigorReleases.total }}</div>
                    <small class="text-muted">最近：{{ vigorReleases.recent }}</small>
                  </div>
                </div>
              </div>
            </div>
        </div>
      </div>

      <!-- organization -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">项目所在组织</h5>
      <div class="m-2 indent-text">
        <small class="text-muted">关注社区的治理结构和运作机制，是评估社区能否高效协调协作、实现长期发展的关键因素。</small>
      </div>
      <div class="card shadow-none border-0 border-bottom rounded-0 mb-3"> <!-- size -->
        <h5 class="m-4 mb-0">规模</h5>
        <div class="m-2 indent-text">
          <small class="text-muted">社区各类成员的数量。规模适中且稳定的团队能够支撑项目的日常维护和创新发展，避免人力资源过度集中或稀缺带来的风险。</small>
        </div>
        <div class="row">
          <!-- 开发者数量 -->
          <div class="col-md-6 mb-3">
            <div class="card m-4 border-0" style="background-color: #FFEBF3;">
              <div class="card-body text-center">
                <h5 class="card-title">开发者</h5>
                <small class="text-muted">所有贡献代码的开发者数量</small>
                <div class="card-text fs-4 text-dark">{{ size['number of contributors']['total'] || 0 }}</div>
                <small class="text-muted">最近：{{ size['number of contributors']['recent'] || 0 }}</small>
              </div>
            </div>
          </div>
          <!-- 核心开发者数量 -->
          <div class="col-md-6 mb-3">
            <div class="card m-4 border-0" style="background-color: #FFEBF3;">
              <div class="card-body text-center">
                <h5 class="card-title">核心开发者</h5>
                <small class="text-muted">具有提交权限的开发者数量</small>
                <div class="card-text fs-4 text-dark">{{ size['number of core contributors'] || 0 }}</div>
                <small class="text-muted" style="visibility: hidden">-</small>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="card shadow-none border-0 border-bottom rounded-0 mb-3"> <!-- diversity -->
        <h5 class="m-4 mb-0">多样性</h5>
        <div class="m-2 indent-text">
          <small class="text-muted">社区成员在各方面的多元化程度。高度多样化的团队有助于促进创新、增强社区韧性，避免单一视角导致的技术或治理盲区。</small>
        </div>
        <div class="m-4 mb-0">公司多样性：见 <a :href="'https://ossinsight.io/analyze/' + repo + '#people'">OSS Insight</a></div>
        <div class="m-4 mb-0">经验多样性</div>
        <div class="m-2 indent-text">
          <small class="text-muted">从 PR 接受率和 Issue 关闭率来侧面反映。</small>
        </div>
        <div class="row m-4">
          <div class="col-md-6 mb-3">
            <div class="card shadow-none border-0 me-4 p-3" style="background-color: #FFFAEB;">
              <h5 class="card-title text-center fs-6">PR接收</h5>
              <div class="row">
                <div class="col-md-6">
                  <v-chart :option="acceptedPRTotalChart" style="height: 250px;" autoresize />
                </div>
                <div class="col-md-6">
                  <v-chart :option="acceptedPRRecentChart" style="height: 250px;" autoresize />
                </div>
              </div>
            </div>
          </div>
          <div class="col-md-6 mb-3">
            <div class="card shadow-none border-0 ms-4 p-3" style="background-color: #FFFAEB;">
              <h5 class="card-title text-center fs-6">Issue关闭</h5>
              <div class="row">
                <div class="col-md-6">
                  <v-chart :option="closedIssueTotalChart" style="height: 250px;" autoresize />
                </div>
                <div class="col-md-6">
                  <v-chart :option="closedIssueRecentChart" style="height: 250px;" autoresize />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="card shadow-none border-0 rounded-0 mb-3"> <!-- rules -->
        <h5 class="m-4 mb-0">规则</h5>
        <div class="m-2 indent-text">
          <small class="text-muted">指社区制定并执行的贡献流程、代码审查规范、角色分工及沟通机制等。明确的规则体系能够保障项目治理的公平性和高效性，提升开发质量和协作体验。</small>
        </div>
        <div class="row m-4">
          <!-- guidance 部分 -->
          <div class="col-md-6 mb-2">
            <h6 class="text-secondary">引导机制 Guidance</h6>

            <ul class="list-group list-group-flush">
              <li v-for="item in guidanceList" :key="item" class="list-group-item px-0 py-1 d-flex align-items-center border-0">
                <span class="badge me-2">✔</span>
                {{ indicatorNames[item] || item }}
              </li>
            </ul>
          </div>
          <!-- incentive system 部分 -->
          <div class="col-md-6 mb-2">
            <h6 class="text-secondary">激励机制 Incentive System</h6>
            <ul class="list-group list-group-flush">
              <li v-for="item in incentiveList" :key="item" class="list-group-item px-0 py-1 d-flex align-items-center border-0">
                <span class="badge me-2">✔</span>
                {{ indicatorNames[item] || item }}
              </li>
            </ul>
          </div>
        </div>
      </div>


      <!-- resilience -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">项目韧性</h5>
      <div class="m-2 indent-text">
        <small class="text-muted">关注社区在面临人员变动、活跃度波动等外部冲击时的承受能力与自我修复能力。</small>
      </div>
      <div class="row mb-4">
        <div class="col-md-6 mb-3 border-end">
          <div class="card shadow-none border-0 rounded-0 mb-3">
            <h5 class="card-title m-4 mb-0">贡献者吸引力</h5>
            <div class="m-2 indent-text">
              <small class="text-muted">社区在一定时间段内吸引新开发者加入并产生贡献的能力。</small>
            </div>
            <div class="card shadow-none border-0 m-4 p-3" style="background-color: #FFF8EB;">
              <h5 class="card-title text-center fs-6">近期新贡献者比例</h5>
              <v-chart :option="attractionChart" style="height: 250px;" autoresize />
            </div>
          </div>
        </div>
        <div class="col-md-6 mb-3">
          <div class="card shadow-none border-0 rounded-0 mb-3">
            <h5 class="card-title m-4 mb-0">贡献者留存力</h5>
            <div class="m-2 indent-text">
              <small class="text-muted">衡量在某一时期内活跃的开发者是否在后续时间段依然持续活跃。</small>
            </div>
            <div class="card shadow-none border-0 m-4 p-3" style="background-color: #FFF8EB;">
              <h5 class="card-title text-center fs-6">近期留存贡献者比例</h5>
              <v-chart :option="retentionChart" style="height: 250px;" autoresize />
            </div>
          </div>
        </div>
      </div>

      <!-- service -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">项目服务能力</h5>
      <div class="m-2 indent-text">
        <small class="text-muted">关注社区所产生的成果是否真正为用户、产业及社会带来价值，强调开源社区作为“公共服务提供者”的角色。</small>
      </div>
      <h5 class="mt-4">流行度</h5>
      <div class="m-2 indent-text mb-3">
        <small class="text-muted">以流行度作为服务能力的外在体现，侧面反映社区对外部用户的吸引力与影响力。</small>
      </div>
      <div class="row mb-4">
        <div class="col-md-3 mb-3">
          <div class="card m-2 border-0" style="background-color: #D9E1FC;">
            <div class="card-body text-center">
              <h5 class="card-title">Stars</h5>
              <p class="card-text fs-4 text-dark">{{ popularity.stars || 0 }}</p>
            </div>
          </div>
        </div>
        <div class="col-md-3 mb-3">
          <div class="card m-2 border-0" style="background-color: #D9E1FC;">
            <div class="card-body text-center">
              <h5 class="card-title">Forks</h5>
              <p class="card-text fs-4 text-dark">{{ popularity.forks || 0 }}</p>
            </div>
          </div>
        </div>
        <div class="col-md-3 mb-3">
          <div class="card m-2 border-0" style="background-color: #D9E1FC;">
            <div class="card-body text-center">
              <h5 class="card-title">Watches</h5>
              <p class="card-text fs-4 text-dark">{{ popularity.watches || 0 }}</p>
            </div>
          </div>
        </div>
        <div class="col-md-3 mb-3">
          <div class="card m-2 border-0 h-75" style="background-color: #D9E1FC;">
            <div class="card-body text-center">
              <h5 class="card-title">Dependents</h5>
              <div class="card-text fs-6 text-dark">repos: {{ popularity.dependents.repositories || 0 }}</div>
              <div class="card-text fs-6 text-dark">packages: {{ popularity.dependents.packages || 0 }}</div>
            </div>
          </div>
        </div>
      </div>
      



    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([TitleComponent, TooltipComponent, LegendComponent, PieChart, CanvasRenderer])

const date = ref('')
const repo = ref('')
const result = ref(null)
const loading = ref(false)

const analyzeHealth = async () => {
  if (!repo.value.trim()) {
    alert('请输入仓库名');
    return;
  }
  result.value = null
  loading.value = true
  try {
    const API_BASE = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, ''); // 去掉末尾/
    const res = await axios.post(`${API_BASE}/health/`, {
      github_repo: repo.value
    })
    date.value = res.data.date
    result.value = res.data.scores
  } catch (error) {
    console.error(error);
    // 如果有响应并存在 detail 字段（FastAPI 的默认格式）
    if (error.response && error.response.data && error.response.data.detail) {
      alert(error.response.data.detail)
    } else {
      alert('分析失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}


// 更新展示数据
//---vigor---
const vigorComments = computed(() => result.value?.vigor?.['communication activity']['number of comments'] ?? {})
const vigorIssues = computed(() => result.value?.vigor?.['communication activity']['number of issues'] ?? {})
const vigorCommits = computed(() => result.value?.vigor?.['development activity']['overall development activity']['number of commits'] ?? {})
const vigorPRs = computed(() => result.value?.vigor?.['development activity']['overall development activity']['number of pull requests'] ?? {})
const vigorReviews = computed(() => result.value?.vigor?.['development activity']['core developer activity']['number of core developer reviews'] ?? {})
const vigorReleases = computed(() => result.value?.vigor?.['release activity']['number of releases'] ?? {})
const requirementCloseTotalChart = computed(() => {
  const vigorRequirement = result.value?.vigor?.['development activity']['overall development activity']["requirement completion ratio"]
  if (!vigorRequirement) return {}
  const closed = vigorRequirement?.['number of requirement issues closed']?.total || 0
  const total = vigorRequirement?.['number of requirement issues']?.total || 0
  const open = total - closed
  return {
    title: {
      text: '总体',
      left: 'center',
      top: 5,
      textStyle: { fontSize: 14 }
    },
    tooltip: { trigger: 'item' },
    series: [{
      name: '关闭比例',
      type: 'pie',
      radius: ['40%', '70%'],
      label: {
        show: true,
        formatter: '{b}: {d}%'
      },
      data: [
        { name: '已关闭', value: closed },
        { name: '未关闭', value: open > 0 ? open : 0 }
      ]
    }]
  }
})
const requirementCloseRecentChart = computed(() => {
  const vigorRequirement = result.value?.vigor?.['development activity']['overall development activity']["requirement completion ratio"]
  if (!vigorRequirement) return {}
  const closed = vigorRequirement?.['number of requirement issues closed']?.recent || 0
  const total = vigorRequirement?.['number of requirement issues']?.recent || 0
  const open = total - closed
  return {
    title: {
      text: '近期',
      left: 'center',
      top: 5,
      textStyle: { fontSize: 14 }
    },
    tooltip: { trigger: 'item' },
    series: [{
      name: '关闭比例',
      type: 'pie',
      radius: ['40%', '70%'],
      label: {
        show: true,
        formatter: '{b}: {d}%'
      },
      data: [
        { name: '已关闭', value: closed },
        { name: '未关闭', value: open > 0 ? open : 0 }
      ]
    }]
  }
})

//organization
const size = computed(() => result.value?.organization?.size ?? {})
const acceptedPRTotalChart = computed(() => {
  const acceptenceData = result.value?.organization?.diversity?.experience?.['acceptence rate of pull requests']
  if (!acceptenceData) return {}

  const merged = acceptenceData?.['number of merged pull requests']?.total || 0
  const total = acceptenceData?.['number of pull requests']?.total || 0
  const unmerged = total - merged

  return {
    title: {
      text: 'PR 合并率（总）',
      left: 'center',
      top: 5,
      textStyle: { fontSize: 14 }
    },
    tooltip: { trigger: 'item' },
    legend: { bottom: 5 },
    series: [{
      name: 'PR 合并比例',
      type: 'pie',
      radius: ['20%', '50%'],
      label: {
        show: false,
        formatter: '{b}: {d}%'
      },
      data: [
        { name: '已合并', value: merged },
        { name: '未合并', value: unmerged > 0 ? unmerged : 0 }
      ]
    }]
  }
})
const acceptedPRRecentChart = computed(() => {
  const acceptenceData = result.value?.organization?.diversity?.experience?.['acceptence rate of pull requests']
  if (!acceptenceData) return {}

  const merged = acceptenceData?.['number of merged pull requests']?.recent || 0
  const total = acceptenceData?.['number of pull requests']?.recent || 0
  const unmerged = total - merged

  return {
    title: {
      text: 'PR 合并率（近期）',
      left: 'center',
      top: 5,
      textStyle: { fontSize: 14 }
    },
    tooltip: { trigger: 'item' },
    legend: { bottom: 5 },
    series: [{
      name: 'PR 合并比例',
      type: 'pie',
      radius: ['20%', '50%'],
      label: {
        show: false,
        formatter: '{b}: {d}%'
      },
      data: [
        { name: '已合并', value: merged },
        { name: '未合并', value: unmerged > 0 ? unmerged : 0 }
      ]
    }]
  }
})
const closedIssueTotalChart = computed(() => {
  const closeData = result.value?.organization?.diversity?.experience?.['close rate of issues']
  if (!closeData) return {}

  const closed = closeData?.['number of issues closed']?.total || 0
  const total = closeData?.['number of issues']?.total || 0
  const open = total - closed

  return {
    title: {
      text: 'Issue 关闭率（总）',
      left: 'center',
      top: 5,
      textStyle: { fontSize: 14 }
    },
    tooltip: { trigger: 'item' },
    legend: { bottom: 5 },
    series: [{
      name: 'Issue 关闭比例',
      type: 'pie',
      radius: ['20%', '50%'],
      label: {
        show: false,
        formatter: '{b}: {d}%'
      },
      data: [
        { name: '已关闭', value: closed },
        { name: '未关闭', value: open > 0 ? open : 0 }
      ]
    }]
  }
})
const closedIssueRecentChart = computed(() => {
  const closeData = result.value?.organization?.diversity?.experience?.['close rate of issues']
  if (!closeData) return {}

  const closed = closeData?.['number of issues closed']?.recent || 0
  const total = closeData?.['number of issues']?.recent || 0
  const open = total - closed

  return {
    title: {
      text: 'Issue 关闭率（近期）',
      left: 'center',
      top: 5,
      textStyle: { fontSize: 14 }
    },
    tooltip: { trigger: 'item' },
    legend: { bottom: 5 },
    series: [{
      name: 'Issue 关闭比例',
      type: 'pie',
      radius: ['20%', '50%'],
      label: {
        show: false,
        formatter: '{b}: {d}%'
      },
      data: [
        { name: '已关闭', value: closed },
        { name: '未关闭', value: open > 0 ? open : 0 }
      ]
    }]
  }
})
const guidanceList = [
  "process maturity",
  "new-comer guidance"
]
const incentiveList = [
  "level of gamification",
  "recognition mechanism",
  "financial support",
  "dynamic developer roles"
]
const indicatorNames = {
  "process maturity": "流程成熟度",
  "new-comer guidance": "新手指引",
  "level of gamification": "游戏化程度",
  "recognition mechanism": "认可机制",
  "financial support": "资金激励机制",
  "dynamic developer roles": "角色流动机制"
}

//resilience
// 吸引力
const attractionChart = computed(() => {
  const newContributors = result.value?.resilience?.attraction["new contributor rate"]
  if (!newContributors) return {}
  const recent = newContributors?.['number of new contributors'] || 0
  const total = newContributors?.['number of contributors'] || 0
  const existing = total - recent
  return {
    tooltip: { trigger: 'item' },
    series: [
      {
        name: '贡献者构成',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        label: {
          show: true,
          formatter: '{b}: {d}%'
        },
        data: [
          { name: '新贡献者', value: recent },
          { name: '既有贡献者', value: existing > 0 ? existing : 0 }
        ]
      }
    ]
  }
})
// 留存力
const retentionChart = computed(() => {
  const retentionContributors = result.value?.resilience?.retention['contributor retention rate']
  if (!retentionContributors) return {}
  const retained = retentionContributors?.['number of retention contributors'] || 0
  const total = retentionContributors?.['number of contributors before'] || 0
  const lost = total - retained
  return {
    tooltip: { trigger: 'item' },
    series: [
      {
        name: '留存情况',
        type: 'pie',
        radius: ['40%', '70%'],
        label: {
          show: true,
          formatter: '{b}: {d}%'
        },
        data: [
          { name: '留存贡献者', value: retained },
          { name: '流失贡献者', value: lost > 0 ? lost : 0 }
        ]
      }
    ]
  }
})

//service
const popularity = computed(() => result.value?.services?.['value']['popularity'] ?? {})

</script>

<style scoped>
.indent-text {
  text-indent: 2em;
  text-align: justify;
}
</style>