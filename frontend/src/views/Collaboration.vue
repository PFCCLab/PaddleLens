<template>

  <div class="container-fluid text-dark text-center py-4 mb-2">
    <h2>社区治理评估</h2>
  </div>

  <div class="container-fluid py-2 mb-3 w-50">
    <div class="row align-items-center g-2">
      <div class="col-auto">
        <label for="repo_governance" class="col-form-label">请输入飞桨相关的 GitHub 仓库名：</label>
      </div>
      <div class="col">
        <div class="input-group">
          <input
            v-model="repo_governance"
            @keyup.enter="analyzeGovernance"
            id="repo_governance"
            class="form-control shadow-none"
            placeholder="例如 PaddlePaddle/Paddle"
          />
          <button @click="analyzeGovernance" class="btn btn-light border">分析</button>
        </div>
      </div>
    </div>
  </div>

  <div class="container w-75 py-4">

    <div v-if="loading" class="text-center">加载中...</div>
    
    <div v-if="result">
      <h4 class="text-center border-top mb-3 py-3 my-3">社区治理成效</h4>

      <div class="m-2 indent-text text-center">
        <p class="text-secondary">最后更新：{{ date }}</p>
        <p class="text-secondary">“近期”指标：最后更新时间的前90天内</p>
      </div>

      <!-- 社区响应 -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">社区响应</h5>
      <div class="m-2 indent-text">
        <small class="text-muted">衡量社区对pr和issue的响应时间。</small>
      </div>
      <div class="row mb-4">
        <div class="col-md-4 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h5 class="card-title">PR响应时间</h5>
              <p class="card-text fs-4 text-dark">{{ prResponseTime || 0 }} h</p>
            </div>
          </div>
        </div>
        <div class="col-md-4 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h5 class="card-title">PR关闭时间</h5>
              <p class="card-text fs-4 text-dark">{{ prCloseTime || 0 }} h</p>
            </div>
          </div>
        </div>
        <div class="col-md-4 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h5 class="card-title">Issue响应时间</h5>
              <p class="card-text fs-4 text-dark">{{ issueResponseTime || 0 }} h</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 社区开放性 -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">社区开放性</h5>

      <div class="m-3">
        <h5 class="mt-4">近期PR提交情况</h5>
      </div>
      <div class="d-flex flex-wrap align-items-end gap-3 m-3 pb-3">
        <div class="fs-6">
          近期有
        </div>
        <div class="display-6 fw-bold" style="color: #F7C572;">
          {{ communityDvprCntRecent }}
        </div>
        <div class="fs-6">
          位社区开发者提交了PR，其中有
        </div>
        <div class="display-6 fw-bold" style="color: #F7C572;">
          {{ communityDvprMergedCntRecent }}
        </div>
        <div class="fs-6">
          位社区开发者的PR已经被合并。
        </div>
      </div>

      <div class="m-3 indent-text">
        <div class="fs-6">近期PR提交最多的前5名社区开发者：</div>
        <ul class="list-group list-group-flush mt-2">
          <li
            v-for="(dev, index) in top5ActiveCommunityDvRecent"
            :key="index"
            class="list-group-item border-0"
          >
            {{ index + 1 }}.
            <a
              :href="`https://github.com/${dev.username}`"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ dev.username }}
            </a>
            - 提交了 {{ dev.pr_cnt }} 个 PR
          </li>
        </ul>
      </div>

      <div class="m-3 border-top">
        <h5 class="mt-4">社区新人PR提交情况</h5>
      </div>
      <div class="d-flex flex-wrap align-items-end gap-3 m-3 pb-3">
        <div class="fs-6">
          近期有
        </div>
        <div class="display-6 fw-bold" style="color: #82E0AA;">
          {{ communityNewcomerPrCntRecent }}
        </div>
        <div class="fs-6">
          个PR是由首次提交PR的开发者提交的，其中有
        </div>
        <div class="display-6 fw-bold" style="color: #82E0AA;">
          {{ communityNewcomerPrMergedCntRecent }}
        </div>
        <div class="fs-6">
          个PR已经被合并。
        </div>
      </div>
    </div>
  </div>

  
  <div class="container w-75 py-4">
    <div class="container-fluid text-center py-4 border-top">
      <h4 class="text-center mb-3 py-3 my-3">附：社区治理框架</h4>
      <div v-if="file_loading" class="text-center">加载中...</div>
      <div v-if="file_result">
        <RecursiveList :data="file_scores" />
      </div>
    </div>

  </div>
  


</template>

<script setup>
import { ref, computed,  onMounted } from 'vue'
import axios from 'axios'
import { use } from 'echarts/core'
import VChart from 'vue-echarts'
import { PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import RecursiveList from '../components/RecursiveList.vue'

use([TitleComponent, TooltipComponent, LegendComponent, PieChart, CanvasRenderer])

const date = ref('')
const repo_governance = ref('')
const result = ref(null)
const loading = ref(false)


const file_result = ref({})
const file_scores = ref(null)
const file_loading = ref(true)


function addSelectionFlags(node) {
  // 如果是叶子节点（数字）就返回自己（0 或 1）
  if (typeof node === 'number') {
    return node
  }

  const result = {}
  let hasSelectedChild = false

  for (const key in node) {
    const child = node[key]
    const processed = addSelectionFlags(child)
    result[key] = processed

    // 如果子节点为 1 或者包含子节点中存在 1，则当前值也设为 1
    const flag = typeof processed === 'number' ? (processed === 1) : (processed._selected === 1)
    if (flag) {
      hasSelectedChild = true
    }
  }

  // 添加一个特殊字段 `_selected` 标记本节点是否被勾选，用于内部逻辑
  result._selected = hasSelectedChild ? 1 : 0
  return result
}

const analyzeRules = async () => {
  try {
    const API_BASE = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, ''); // 去掉末尾/
    const res = await axios.get(`${API_BASE}/governance/`)
    file_result.value = res.data

    // file_scores.value = addAveragesPreserveLeaves(file_result.value.scores)
    file_scores.value = addSelectionFlags(file_result.value.scores)

  } catch (error) {
    console.error(error);
    alert('展示失败')
  } finally {
    file_loading.value = false
  }
}

onMounted(() => {
  analyzeRules()
})



const analyzeGovernance = async () => {
  if (!repo_governance.value.trim()) {
    alert('请输入仓库名');
    return;
  }
  result.value = null
  loading.value = true
  try {
    const API_BASE = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, ''); // 去掉末尾/
    const res = await axios.post(`${API_BASE}/governance/`, {
      github_repo: repo_governance.value
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
//--社区响应--
const prResponseTime = computed(() => result.value?.response_time?.['pr_response_time_recent'] ?? 0)  //最近pr响应时间，单位：h
const prCloseTime = computed(() => result.value?.response_time?.['pr_close_time_recent'] ?? 0)  //最近pr关闭时间，单位：h
const issueResponseTime = computed(() => result.value?.response_time?.['issue_response_time_recent'] ?? 0)  //最近issue响应时间，单位：h

//--社区开放性--

const communityDvprCntRecent = computed(() => result.value?.community_developer_activity?.['community_developer_cnt_recent'] ?? 0)  //近期提交pr的开发者人数
const communityDvprMergedCntRecent = computed(() => result.value?.community_developer_activity?.['community_developer_merged_cnt_recent'] ?? 0)  //近期提交并合并pr的开发者人数



const communityNewcomerPrCntRecent = computed(() => result.value?.community_developer_activity?.['community_newcomer_pr_cnt_recent'] ?? 0)  //近期首次提交pr的开发者的pr数
const communityNewcomerPrMergedCntRecent = computed(() => result.value?.community_developer_activity?.['community_newcomer_pr_merged_cnt_recent'] ?? 0)  //近期首次提交并合并的开发者的pr数


const top5ActiveCommunityDvRecent = computed(() => {
  const rawList = result.value?.community_developer_activity?.['top5_active_community_developers_recent'] ?? []
  return Array.isArray(rawList)
    ? rawList.map(([username, pr_cnt]) => ({ username, pr_cnt }))
    : []
})  //近期pr提交数最多的前5名社区开发者



</script>