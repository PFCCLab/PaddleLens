<template>
  <div class="p-3">
    <div v-for="(value, key) in data" :key="key" class="list-group-item m-1">
      <!-- 渲染每一个指标 -->
      <div v-if="key !== '_selected'" class="d-flex justify-content-between align-items-center p-3 border-0 rounded" style="background-color: #F0F3F5;">
        <div>
          <!-- 折叠按钮，仅当是对象时显示 -->
          <button v-if="isObject(value)" class="btn btn-sm btn-link p-0 me-2" @click="toggleCollapse(key)">
            <span>{{ ensureCollapse(key) ? '▼' : '▶' }}</span>
          </button>
          <!-- 名称和描述 -->
          <strong>{{ key }}</strong>
          <small class="text-muted ms-2">{{ descMap[key] || '' }}</small>
        </div>
        <!-- 得分 -->
        <span v-if="getSelected(value) === 1" :class="['badge', 'rounded-pill']">
          ✔
        </span>
      </div>

      <!-- 递归渲染，需要是对象且处于展开状态 -->
      <div v-if="isObject(value) && ensureCollapse(key)" class="ms-3 me-3 border-start">
        <RecursiveList :data="value" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, ref } from 'vue'

const props = defineProps({
  data: {
    type: Object,
    required: true
  }
})


// 中文描述映射
const descMap = {
  // 职位规则
  职位规则: '项目中的权限划分和职责分工，明确各类参与者的角色与权限，保障治理的清晰与高效。',
  权限划分: '明确不同参与者在项目中的权限等级与任务职责范围。',
  问题分类者: '负责初步分类问题与任务，确保问题分发流程顺畅。',
  审核者: '有权限审核和把关贡献的角色，保障项目质量与规范。',
  提交者: '具备代码提交权限的核心角色，负责编码质量与一致性。',
  模块划分: '对项目模块进行责任划分，确保模块维护清晰。',
  代码所有者: '对特定代码模块负责的人员，拥有修改与审核权限。',
  模块维护者: '负责指定模块的维护与演进，提升代码质量。',
  项目维护者: '负责项目总体技术方向与管理任务，统筹开发流程。',

  // 边界规则
  边界规则: '角色的资格判定与任命方式，确保社区人员选拔公正高效。',
  角色资质评估: '评估社区参与者能否担任关键角色的标准与条件。',
  参与历史: '参考社区参与者以往的活跃程度与参与质量。',
  价值观契合度: '考察参与者在价值观及行为规范上的一致性。',
  提名: '通过推荐机制选出候选角色人员。',
  角色任命流程: '从评估到正式赋予角色的操作流程与审核机制。',

  // 选择规则
  选择规则: '为参与者提供入门支持与开发引导，帮助其顺利参与治理与开发。',
  入职支持: '为新加入者提供必要资料与任务引导，减少上手门槛。',
  教程: '帮助新手理解项目结构与操作方式的指导文档。',
  任务推荐: '指导贡献者挑选适合的任务快速上手。',
  指导支持: '项目为贡献者提供的人员引导和协作帮助。',
  开发指南: '参与开发所需遵循的一系列技术规范与设备配置说明。',
  软硬件要求: '项目运行和开发所需的基本设施配置说明。',
  开发环境设置指南: '如何搭建本地开发环境以启动项目。',
  变更提交指南: '如何撰写、整理和提交代码或文档的流程规范。',
  CI描述: '持续集成工具的使用说明，包括运行环境及异常处理。',
  开发工具指南: '推荐使用的开发工具及配置建议。',
  贡献者许可协议: '贡献者在提交代码前需确认的法律协议（如 CLA）。',

  // 范围规则
  范围规则: '对项目贡献标准、问题模板和 PR 提交要求的详细定义。',
  问题模板: '社区中用于报告问题（issue）的标准化模板。',
  贡献规范: '规范贡献内容的质量与格式，确保规范协调。',
  代码价值观: '项目倡导的代码质量与协作准则。',
  代码风格规范: '代码编辑时需遵循的格式与风格要求。',
  文档风格规范: '文档撰写所需的语言风格与结构指南。',
  测试规范: '撰写测试用例与执行测试的推荐方式。',
  PR标准: '对 Pull Request 的格式、规模和提交模板的要求。',
  PR大小要求: '对 PR 提交大小（行数/文件）的控制建议。',
  PR模板: '统一 PR 描述格式，用于审核与记录。',

  // 聚合规则
  聚合规则: '项目设计与补丁的提交评审流程，便于社区集中意见并推动实现。',
  设计提案流程: '对功能提案的提交、讨论与采纳流程的定义。',
  补丁评审流程: '用于审核和合并补丁（patch）的评审规则和流程。',

  // 信息规则
  信息规则: '信息流转机制的定义，确保沟通顺畅且信息传递及时。',
  沟通渠道: '提供官方沟通路径，如邮件、群组、chat 等。',
  通知机制: '变更或公告等信息如何通知贡献者。',

  // 奖惩规则
  奖惩规则: '对积极贡献行为的激励机制，以及对不当行为的规范与惩戒标准。',
  激励机制: '通过荣誉、物质或身份等手段激励优秀贡献者。',
  行为准则: '参与社区必须遵守的行为规范与合作守则。'
}

// 判断是否为对象（非叶子节点）
const isObject = (val) => typeof val === 'object' && val !== null

// 控制折叠状态（按 key 存储）
const collapsedKeys = ref({})
//查询展开状态
const ensureCollapse = (key) => {
  if (!(key in collapsedKeys.value)) {
    collapsedKeys.value[key] = false
  }
  return collapsedKeys.value[key]
}
// 折叠/展开切换
const toggleCollapse = (key) => {
  collapsedKeys.value[key] = !collapsedKeys.value[key]
}

const getSelected = (val) => {
  if (typeof val === 'number') {
    return val
  }
  return val?._selected || 0
}

</script>

<style scoped>
button {
  color: black;
  text-decoration: none;
}
</style>