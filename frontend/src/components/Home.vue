<template>
  <div>
    <div class="container-fluid text-dark text-center py-5 mb-4 d-flex flex-column justify-content-center" style="background-color: #f8f9fa; height: 400px">
      <h1 class="display-4 fw-bold">PaddleLens</h1>
      <p class="text">飞桨开源社区度量平台</p>
    </div>

    <div class="container-fluid border-0 text-center min-vh-100 my-5 px-5">
      <div class="row g-0">
        <router-link to="/developerskills" class="text-decoration-none col-md-4">
          <div class="p-4 h-100 border-end text-dark text-center hover-card">
            <h4 class="mb-3">👨‍💻 开发者能力度量</h4>
            <p class="text-muted">基于github行为数据分析与评估开发者能力。</p>
          </div>
        </router-link>

        <router-link to="/collaboration" class="text-decoration-none col-md-4">
          <div class="p-4 h-100 border-end text-dark text-center hover-card">
            <h4 class="mb-3">🤝 社区治理评估</h4>
            <p class="text-muted">基于github项目数据度量开源社区治理规则及成效。</p>
          </div>
        </router-link>

        <router-link to="/community" class="text-decoration-none col-md-4">
          <div class="p-4 h-100 text-dark text-center hover-card">
            <h4 class="mb-3">🌱 社区健康度度量</h4>
            <p class="text-muted">基于github项目数据度量开源社区健康度。</p>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<style>
.hover-card {
  transition: all 0.2s ease;
}

.hover-card:hover {
  transform: translateY(-2px);
  cursor: pointer;
}
</style>