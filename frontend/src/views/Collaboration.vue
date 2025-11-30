<template>

  <div class="container-fluid text-dark text-center py-4 mb-2">
    <h2>社区治理评估</h2>
  </div>

  <div class="container-fluid py-2 mb-3 w-25">
    <div class="row align-items-center g-2">
      <div class="col-auto">
        <label for="input_date" class="col-form-label">请选择分析日期：</label>
      </div>
      <div class="col">
        <div class="input-group">
          <input
            type="date"
            id="input_date"
            v-model="input_date"
            class="form-control shadow-none"
          />
          <button @click="analyzeGovernance" class="btn btn-light border">
            分析
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="container w-75 py-4">

    <div v-if="loading" class="text-center">加载中...</div>

    <div v-if="rules">
      <h4 class="text-center border-top mb-3 py-3 my-3">社区治理规则</h4>

      <div v-if="new_rule.length > 0" class="m-3 p-3 rounded">
        <h6 class="mb-3">该日期新增规则</h6>
        <ul>
          <li v-for="(item, index) in new_rule" :key="index">
            {{ item }}
          </li>
        </ul>
      </div>

      <div>
        <h6 class="m-3 ps-3">该日期已有规则</h6>
        <ul>
          <li v-for="(value1, key1) in rules" :key="key1">
            <div class="bg-light">
              <h5 class="mb-3 py-3 m-3">{{ key1 }}</h5>
            </div>
            <ul>
              <!-- 第二层 -->
              <li v-for="(value2, key2) in value1" :key="key2">
                <!-- 如果是 general 则直接展开内容 -->
                <template v-if="key2 === '_general'">
                  <li v-for="(item, index) in value2" :key="index">{{ item }}</li>
                </template>
                <template v-else>
                  <strong>{{ key2 }}:</strong>
                  <ul>
                    <!-- 第三层 -->
                    <li v-for="(value3, key3) in value2" :key="key3">
                      <template v-if="key3 === '_general'">
                        <li v-for="(item, index) in value3" :key="index">{{ item }}</li>
                      </template>
                      <template v-else>
                        <strong>{{ key3 }}:</strong>
                        <ul>
                          <li v-for="(item, index) in value3" :key="index">{{ item }}</li>
                        </ul>
                      </template>
                    </li>
                  </ul>
                </template>
              </li>
            </ul>
          </li>
        </ul>
      </div>
      
    </div>

    <div v-if="scores">
      <h4 class="text-center border-top mb-3 py-3 my-3">社区治理成效</h4>

      <div class="m-2 indent-text text-center">
        <p class="text-secondary">数据最后更新：{{ date }}</p>
        <!-- <p class="text-secondary">“近期”指标：最后更新时间的前90天内</p> -->
      </div>

      <!-- 社区响应 -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">社区响应</h5>
      <div class="row mb-4">
        <div class="col-md-4 mb-3">
          <div class="m-3">
            <h5 class="mt-4">PR响应时间</h5>
          </div>
          <div class="m-2 indent-text">
            <small class="text-muted">该时间段内该PR第一个审查或评论时间的中位数。</small>
          </div>
          <div class="card m-3 border-0" style="background-color: #EBEBEB;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点前3个月</h6>
              <p class="card-text fs-4 text-dark">{{ prResponseTimeBefore || 0 }} h</p>
            </div>
          </div>
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点后3个月</h6>
              <p class="card-text fs-4 text-dark">{{ prResponseTimeAfter || 0 }} h</p>
            </div>
          </div>
        </div>
        <div class="col-md-4 mb-3">
          <div class="m-3">
            <h5 class="mt-4">PR关闭时间</h5>
          </div>
          <div class="m-2 indent-text">
            <small class="text-muted">该时间段内PR被关闭或合并时间的中位数。</small>
          </div>
          <div class="card m-3 border-0" style="background-color: #EBEBEB;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点前3个月</h6>
              <p class="card-text fs-4 text-dark">{{ prCloseTimeBefore || 0 }} h</p>
            </div>
          </div>
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点后3个月</h6>
              <p class="card-text fs-4 text-dark">{{ prCloseTimeAfter || 0 }} h</p>
            </div>
          </div>
        </div>
        <div class="col-md-4 mb-3">
          <div class="m-3">
            <h5 class="mt-4">Issue响应时间</h5>
          </div>
          <div class="m-2 indent-text">
            <small class="text-muted">该时间段内社区对issue第一次评论时间的中位数。</small>
          </div>
          <div class="card m-3 border-0" style="background-color: #EBEBEB;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点前3个月</h6>
              <p class="card-text fs-4 text-dark">{{ issueResponseTimeBefore || 0 }} h</p>
            </div>
          </div>
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点后3个月</h6>
              <p class="card-text fs-4 text-dark">{{ issueResponseTimeAfter || 0 }} h</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 社区吸引力 -->
      <h5 class="text-center bg-light mb-3 py-3 my-3">社区贡献者吸引力</h5>

      <div class="m-3">
        <h5 class="mt-4">提交PR的新手人数</h5>
      </div>
      <div class="m-2 indent-text">
        <small class="text-muted">该时间段内第一次为社区提交PR的贡献者数量。</small>
      </div>
      <div class="row mb-4">
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBEBEB;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点前3个月</h6>
              <p class="card-text fs-4 text-dark">{{ newcomerCntBefore || 0 }} 人</p>
            </div>
          </div>
        </div>
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点后3个月</h6>
              <p class="card-text fs-4 text-dark">{{ newcomerCntAfter || 0 }} 人</p>
            </div>
          </div>
        </div>
      </div>

      <div class="m-3">
        <h5 class="mt-4">新手提交的PR数</h5>
      </div>
      <div class="m-2 indent-text">
        <small class="text-muted">该时间段内由新手提交的PR数量。</small>
      </div>
      <div class="row mb-4">
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBEBEB;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点前3个月</h6>
              <p class="card-text fs-4 text-dark">{{ newcomerPrCntBefore || 0 }} 个</p>
            </div>
          </div>
        </div>
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点后3个月</h6>
              <p class="card-text fs-4 text-dark">{{ newcomerPrCntAfter || 0 }} 个</p>
            </div>
          </div>
        </div>
      </div>

      <div class="m-3">
        <h5 class="mt-4">新手PR数在当期PR数占比</h5>
      </div>
      <div class="m-2 indent-text">
        <small class="text-muted">该时间段内新手提交的PR数量 ÷ 该时间段内提交的所有PR数量 × 100% 。</small>
      </div>
      <div class="row mb-4">
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBEBEB;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点前3个月</h6>
              <p class="card-text fs-4 text-dark">{{ (newcomerPrRatioBefore || 0).toFixed(2) }} %</p>
            </div>
          </div>
        </div>
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点后3个月</h6>
              <p class="card-text fs-4 text-dark">{{ (newcomerPrRatioAfter || 0).toFixed(2) }} %</p>
            </div>
          </div>
        </div>
      </div>
      
      <div class="m-3">
        <h5 class="mt-4">新手合并的PR数</h5>
      </div>
      <div class="m-2 indent-text">
        <small class="text-muted">该时间段内由新手提交，并且被合并的PR数量。</small>
      </div>
      <div class="row mb-4">
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBEBEB;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点前3个月</h6>
              <p class="card-text fs-4 text-dark">{{ newcomerMergedCntBefore || 0 }} 个</p>
            </div>
          </div>
        </div>
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点后3个月</h6>
              <p class="card-text fs-4 text-dark">{{ newcomerMergedCntAfter || 0 }} 个</p>
            </div>
          </div>
        </div>
      </div>

      <div class="m-3">
        <h5 class="mt-4">新手PR合并率</h5>
      </div>
      <div class="m-2 indent-text">
        <small class="text-muted">该时间段内新手被合并的PR数量 ÷ 该时间段内新手提交的PR数量 × 100% 。</small>
      </div>
      <div class="row mb-4">
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBEBEB;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点前3个月</h6>
              <p class="card-text fs-4 text-dark">{{ (newcomerPrMergedRatioBefore || 0).toFixed(2) }} %</p>
            </div>
          </div>
        </div>
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点后3个月</h6>
              <p class="card-text fs-4 text-dark">{{ (newcomerPrMergedRatioAfter || 0).toFixed(2) }} %</p>
            </div>
          </div>
        </div>
      </div>

      <div class="m-3">
        <h5 class="mt-4">来自非百度员工的新手占比</h5>
      </div>
      <div class="m-2 indent-text">
        <small class="text-muted">该时间段内提交PR的非百度新手数量 ÷ 该时间段内提交PR的所有新手数量 × 100% 。其中，“非百度员工”的判断步骤为：1）合并相同邮箱不同用户名的开发者；2）迭代合并有邮箱重叠的开发者名组，得到唯一开发者；3）唯一开发者的邮件地址不包含“baidu.com”或“paddle”。</small>
      </div>
      <div class="row mb-4">
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBEBEB;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点前3个月</h6>
              <p class="card-text fs-4 text-dark">{{ (newcomerAffiliationRatioBefore || 0).toFixed(2) }} %</p>
            </div>
          </div>
        </div>
        <div class="col-md-6 mb-3">
          <div class="card m-3 border-0" style="background-color: #EBFCD9;">
            <div class="card-body text-center">
              <h6 class="card-title">时间点后3个月</h6>
              <p class="card-text fs-4 text-dark">{{ (newcomerAffiliationRatioAfter || 0).toFixed(2) }} %</p>
            </div>
          </div>
        </div>
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
// import RecursiveList from '../components/RecursiveList.vue'

use([TitleComponent, TooltipComponent, LegendComponent, PieChart, CanvasRenderer])

const date = ref('')
const repo_governance = ref('')
const scores = ref(null)
const rules = ref(null)
const new_rule = ref(null)
const loading = ref(false)


// 分析仓库治理情况
const analyzeGovernance = async () => {
  if (!input_date.value) {
    alert('请输入日期');
    return;
  }
  scores.value = null
  loading.value = true
  try {
    const API_BASE = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, ''); // 去掉末尾/
    const res = await axios.post(`${API_BASE}/governance/`, {
      input_date: input_date.value
    })
    date.value = res.data.date
    scores.value = res.data.scores
    rules.value = res.data.rules
    new_rule.value = res.data.new_rule
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

//before
const prResponseTimeBefore = computed(() => scores.value?.response_time?.before?.['pr_response_time_before'] ?? 0)  //之前pr响应时间，单位：h
const prCloseTimeBefore = computed(() => scores.value?.response_time?.before?.['pr_close_time_before'] ?? 0)  //之前pr关闭时间，单位：h
const issueResponseTimeBefore = computed(() => scores.value?.response_time?.before?.['issue_response_time_before'] ?? 0)  //之前issue响应时间，单位：h

//after
const prResponseTimeAfter = computed(() => scores.value?.response_time?.after?.['pr_response_time_after'] ?? 0)  //之后pr响应时间，单位：h
const prCloseTimeAfter = computed(() => scores.value?.response_time?.after?.['pr_close_time_after'] ?? 0)  //之后pr关闭时间，单位：h
const issueResponseTimeAfter = computed(() => scores.value?.response_time?.after?.['issue_response_time_after'] ?? 0)  //之后issue响应时间，单位：h

//--社区新手--

//before
const newcomerCntBefore = computed(() => scores.value?.community_developer_activity?.before?.['community_newcomer_cnt_before'] ?? 0)  //之前提交pr的新手人数
const newcomerPrCntBefore = computed(() => scores.value?.community_developer_activity?.before?.['community_newcomer_pr_cnt_before'] ?? 0)  //之前的新手的pr数
const newcomerPrRatioBefore = computed(() => scores.value?.community_developer_activity?.before?.['community_newcomer_pr_cnt_ratio_before']*100 ?? 0)  //之前的新手的pr占当时总提交pr的比例
const newcomerMergedCntBefore = computed(() => scores.value?.community_developer_activity?.before?.['community_newcomer_pr_merged_cnt_before'] ?? 0)  //之前新手的pr合并数
const newcomerPrMergedRatioBefore = computed(() => scores.value?.community_developer_activity?.before?.['community_newcomer_pr_merged_cnt_ratio_before']*100 ?? 0)  //之前新手的pr合并率
const newcomerAffiliationRatioBefore = computed(() => scores.value?.community_developer_activity?.before?.['community_newcomer_affiliation_ratio_before']*100 ?? 0)  //之前新手归属于社区的比例

//after
const newcomerCntAfter = computed(() => scores.value?.community_developer_activity?.after?.['community_newcomer_cnt_after'] ?? 0)  //之后提交pr的新手人数
const newcomerPrCntAfter = computed(() => scores.value?.community_developer_activity?.after?.['community_newcomer_pr_cnt_after'] ?? 0)  //之后的新手的pr数
const newcomerPrRatioAfter = computed(() => scores.value?.community_developer_activity?.after?.['community_newcomer_pr_cnt_ratio_after']*100 ?? 0)  //之后的新手的pr占当时总提交pr的比例
const newcomerMergedCntAfter = computed(() => scores.value?.community_developer_activity?.after?.['community_newcomer_pr_merged_cnt_after'] ?? 0)  //之后新手的pr合并数
const newcomerPrMergedRatioAfter = computed(() => scores.value?.community_developer_activity?.after?.['community_newcomer_pr_merged_cnt_ratio_after']*100 ?? 0)  //之后新手的pr合并率
const newcomerAffiliationRatioAfter = computed(() => scores.value?.community_developer_activity?.after?.['community_newcomer_affiliation_ratio_after']*100 ?? 0)  //之后新手归属于社区的比例

// --治理规则--

const parsedNewRules = (new_rule.value || []).map(ruleStr => {
  const [path, description] = ruleStr.split(' : ')
  return {
    path: path.trim(),
    description: description.trim()
  }
})



</script>