<script setup>
import { computed, ref } from 'vue'
import LoginView from './components/LoginView.vue'
import LiveTrips from './components/LiveTrips.vue'
import TripsView from './components/TripsView.vue'
import MapView from './components/MapView.vue'
import HistoryView from './components/HistoryView.vue'
import PlanningView from './components/PlanningView.vue'
import { getToken, clearToken } from './api/client'

const isAuthenticated = ref(Boolean(getToken()))

function handleLoginSuccess() {
  isAuthenticated.value = true
}

function handleLogout() {
  clearToken()
  isAuthenticated.value = false
  currentPage.value = 'dashboard'
}

const menu = [
  { id: 'dashboard', icon: '', label: '工作台' },
  { id: 'trips', icon: '', label: '我的旅行' },
  { id: 'planning', icon: '', label: 'AI 智能规划' },
  { id: 'map', icon: '', label: '地图与路线' },
  { id: 'history', icon: '', label: '历史版本' },
]

const currentPage = ref('dashboard')
const selectedDay = ref(0)

const itinerary = [
  {
    date: '2027-04-03',
    label: '第 1 天',
    theme: '西湖城市观光',
    items: [
      { time: '09:00 - 13:30', name: '杭州西湖风景名胜区', type: '自然风光' },
    ],
  },
  {
    date: '2027-04-04',
    label: '第 2 天',
    theme: '寺庙文化与自然探索',
    items: [
      { time: '09:00 - 12:00', name: '灵隐寺', type: '历史文化' },
      { time: '13:30 - 17:30', name: '西溪国家湿地公园', type: '自然风光' },
    ],
  },
  {
    date: '2027-04-05',
    label: '第 3 天',
    theme: '老城区漫步',
    items: [
      { time: '09:00 - 11:30', name: '南宋御街', type: '城市漫步' },
      { time: '13:00 - 15:30', name: '河坊街', type: '美食街区' },
    ],
  },
]

const pageTitle = computed(
  () => menu.find(item => item.id === currentPage.value)?.label || '工作台'
)

const activeDay = computed(() => itinerary[selectedDay.value])

function goTo(id) {
  currentPage.value = id
}
</script>

<template>
  <LoginView
    v-if="!isAuthenticated"
    @success="handleLoginSuccess"
  />
  <div v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon"></div>
        <div>
          <div class="brand-name">TripMate <span>AI</span></div>
          <div class="brand-subtitle">智能旅行规划平台</div>
        </div>
      </div>

      <div class="sidebar-label">工作空间</div>

      <nav class="navigation">
        <button
          v-for="item in menu"
          :key="item.id"
          class="nav-item"
          :class="{ active: currentPage === item.id }"
          @click="goTo(item.id)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
          <span v-if="currentPage === item.id" class="nav-indicator"></span>
        </button>
      </nav>

      <div class="sidebar-bottom">
        <div class="sidebar-tip">
          <div class="tip-icon"></div>
          <strong>让旅行更轻松</strong>
          <p>AI 推荐目的地景点，智能安排每日游玩路线。</p>
          <button @click="goTo('planning')">探索智能规划 </button>
        </div>

        <div class="sidebar-profile">
          <div class="avatar">T</div>
          <div>
            <strong>TripMate 用户</strong>
            <small>本地开发环境</small>
          </div>
          <span class="profile-dot"></span>
        </div>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="breadcrumb">工作空间 <span>/</span> {{ pageTitle }}</div>
        <div class="topbar-right">
          <span class="env-tag"><span class="green-dot"></span> 已登录</span>
          <button class="logout-button" @click="handleLogout">
            退出登录
          </button>
          <div class="top-avatar">T</div>
        </div>
      </header>

      <main class="content">
        <template v-if="currentPage === 'dashboard'">
          <LiveTrips />
          <div class="welcome">
            <div>
              <div class="eyebrow">TRIPMATE AI  YOUR TRAVEL COPILOT</div>
              <h1>开启下一段精彩旅程 <span></span></h1>
              <p>从灵感到出发，用 AI 让每一次旅行都恰到好处。</p>
            </div>
            <button class="primary-btn" @click="goTo('planning')">
               开始 AI 规划 <span></span>
            </button>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-top"><span class="stat-icon blue"></span><span></span></div>
              <div class="stat-number">01</div>
              <div class="stat-label">旅行项目</div>
            </div>
            <div class="stat-card">
              <div class="stat-top"><span class="stat-icon purple"></span><span></span></div>
              <div class="stat-number">03</div>
              <div class="stat-label">历史规划版本</div>
            </div>
            <div class="stat-card">
              <div class="stat-top"><span class="stat-icon cyan"></span><span></span></div>
              <div class="stat-number">05</div>
              <div class="stat-label">本次行程景点</div>
            </div>
            <div class="stat-card">
              <div class="stat-top"><span class="stat-icon green"></span><span></span></div>
              <div class="stat-number">100<span class="small-unit">分</span></div>
              <div class="stat-label">最新行程质量评分</div>
            </div>
          </div>

          <div class="section-heading">
            <div>
              <h2>我的旅行计划</h2>
              <p>旅行灵感、行程安排，一站式管理</p>
            </div>
            <button class="text-btn" @click="goTo('trips')">查看全部 </button>
          </div>

          <div class="trip-card">
            <div class="trip-visual">
              <div class="trip-image-overlay"></div>
              <div class="image-label">CHINA  HANGZHOU</div>
              <div class="trip-image-title">杭州<br />三日游</div>
            </div>

            <div class="trip-details">
              <div class="trip-meta">
                <span class="status-pill"> 已生成行程</span>
                <span class="version-pill">v3 最新版本</span>
              </div>
              <h3>杭州三日游</h3>
              <p class="trip-subtitle">漫步西湖  探索灵隐  发现杭州之美</p>

              <div class="trip-facts">
                <span> 2027.04.03  04.05</span>
                <span> 杭州</span>
                <span> 2 人出行</span>
              </div>

              <div class="trip-actions">
                <button class="primary-btn" @click="goTo('planning')">查看行程 </button>
                <button class="outline-btn" @click="goTo('history')">历史版本</button>
              </div>
            </div>
          </div>

          <div class="section-heading schedule-heading">
            <div>
              <h2>每日行程预览</h2>
              <p>按天查看游玩安排，轻松掌握旅行节奏</p>
            </div>
          </div>

          <div class="schedule-card">
            <div class="day-tabs">
              <button
                v-for="(day, index) in itinerary"
                :key="day.date"
                :class="{ selected: selectedDay === index }"
                @click="selectedDay = index"
              >
                {{ day.label }}
                <small>{{ day.date.slice(5) }}</small>
              </button>
            </div>

            <div class="day-content">
              <div class="day-title">
                <div>
                  <span class="blue-label">DAY 0{{ selectedDay + 1 }}</span>
                  <h3>{{ activeDay.theme }}</h3>
                </div>
                <span class="activity-count">{{ activeDay.items.length }} 个游玩地点</span>
              </div>

              <div class="timeline">
                <div
                  v-for="(item, index) in activeDay.items"
                  :key="index"
                  class="timeline-item"
                >
                  <div class="timeline-marker"></div>
                  <div class="timeline-time">{{ item.time }}</div>
                  <div class="timeline-info">
                    <strong>{{ item.name }}</strong>
                    <span>{{ item.type }}</span>
                  </div>
                  <span class="timeline-arrow"></span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="subpage-header">
            <span class="eyebrow">TRIPMATE AI</span>
            <h1>{{ pageTitle }}</h1>
            <p>模块界面已建立，接下来逐步连接 FastAPI 和 MySQL。</p>
          </div>

          <TripsView v-if="currentPage === 'trips'" />

          <PlanningView v-else-if="currentPage === 'planning'" />
          <HistoryView v-else-if="currentPage === 'history'" />

          <MapView v-else-if="currentPage === 'map'" />
        </template>

        <footer class="footer">
          <span> 2026 TripMate AI  智能旅行规划平台</span>
          <span>Vue 3 + FastAPI + LangGraph</span>
        </footer>
      </main>
    </div>
  </div>
</template>



