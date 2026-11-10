<script setup>
import { onMounted, ref } from 'vue'
import {
  getTrips,
  getItineraryVersions,
  getItineraryDetail,
} from '../api/client'

const trips = ref([])
const selectedTrip = ref(null)
const versions = ref([])
const tripVersionCounts = ref({})
const currentVersion = ref(null)
const itineraryDetail = ref(null)

const loading = ref(false)
const detailLoading = ref(false)
const errorMessage = ref('')

function normalizeTrips(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.trips)) return data.trips
  if (Array.isArray(data?.items)) return data.items
  if (Array.isArray(data?.data)) return data.data
  if (Array.isArray(data?.data?.trips)) {
    return data.data.trips
  }

  throw new Error('旅行项目接口返回格式不符合预期')
}

async function loadTrips() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await getTrips()
    trips.value = normalizeTrips(response)

    const counts = {}

    await Promise.all(
      trips.value.map(async trip => {
        try {
          const data = await getItineraryVersions(trip.id)
          counts[trip.id] = Array.isArray(data.versions)
            ? data.versions.length
            : 0
        } catch {
          counts[trip.id] = null
        }
      })
    )

    tripVersionCounts.value = counts

    if (trips.value.length > 0) {
      await selectTrip(trips.value[0])
    } else {
      selectedTrip.value = null
      versions.value = []
      itineraryDetail.value = null
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

async function selectTrip(trip) {
  selectedTrip.value = trip
  versions.value = []
  itineraryDetail.value = null
  currentVersion.value = null
  errorMessage.value = ''

  try {
    const response = await getItineraryVersions(trip.id)

    versions.value = Array.isArray(response.versions)
      ? response.versions
      : []

    if (versions.value.length > 0) {
      await selectVersion(versions.value[0].version)
    }
  } catch (error) {
    errorMessage.value = error.message
  }
}

async function selectVersion(version) {
  if (!selectedTrip.value) return

  detailLoading.value = true
  errorMessage.value = ''

  try {
    const response = await getItineraryDetail(
      selectedTrip.value.id,
      version,
    )

    itineraryDetail.value = response
    currentVersion.value = version
  } catch (error) {
    itineraryDetail.value = null
    errorMessage.value = error.message
  } finally {
    detailLoading.value = false
  }
}

function formatDate(date) {
  if (!date) return '未设置日期'
  return String(date).slice(0, 10)
}

function formatTime(time) {
  return String(time || '').slice(0, 5)
}

onMounted(loadTrips)
</script>

<template>
  <div class="trips-page">
    <div class="page-heading">
      <div>
        <span class="page-eyebrow">MY TRAVEL PLANS</span>
        <h2>我的旅行项目</h2>
        <p>查看已创建的旅行及 AI 生成的历史行程。</p>
      </div>

      <button
        class="refresh-button"
        :disabled="loading"
        @click="loadTrips"
      >
        {{ loading ? '加载中...' : '刷新数据' }}
      </button>
    </div>

    <div v-if="errorMessage" class="error-box">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="empty-box">
      正在从 MySQL 读取旅行项目...
    </div>

    <template v-else>
      <div v-if="trips.length === 0" class="empty-box">
        <h3>暂无旅行项目</h3>
        <p>当前账号还没有创建旅行项目。</p>
      </div>

      <template v-else>
        <div class="project-grid">
          <button
            v-for="trip in trips"
            :key="trip.id"
            class="project-card"
            :class="{
              selected: selectedTrip?.id === trip.id
            }"
            @click="selectTrip(trip)"
          >
            <div class="project-top">
              <span class="project-tag">旅行项目</span>
              <span class="project-id">#{{ trip.id }}</span>
            </div>

            <h3>{{ trip.title }}</h3>
            <p>目的地：{{ trip.destination }}</p>

            <div class="project-bottom">
              <span :class="{ 'trip-planned': tripVersionCounts[trip.id] > 0 }">
              {{
                tripVersionCounts[trip.id] == null
                  ? '状态暂不可用'
                  : tripVersionCounts[trip.id] > 0
                    ? '已生成 AI 行程'
                    : '待生成 AI 行程'
              }}
            </span>
              <span>查看详情 </span>
            </div>
          </button>
        </div>

        <section v-if="selectedTrip" class="detail-panel">
          <div class="detail-heading">
            <div>
              <span class="page-eyebrow">
                SELECTED TRIP
              </span>
              <h2>{{ selectedTrip.title }}</h2>
              <p>
                旅行目的地：{{ selectedTrip.destination }}
              </p>
            </div>

            <span class="project-tag">
              项目 ID：{{ selectedTrip.id }}
            </span>
          </div>

          <div class="version-section">
            <div class="version-header">
              <h3>历史规划版本</h3>
              <span>共 {{ versions.length }} 个版本</span>
            </div>

            <div v-if="versions.length" class="version-buttons">
              <button
                v-for="item in versions"
                :key="item.version"
                :class="{
                  active: currentVersion === item.version
                }"
                @click="selectVersion(item.version)"
              >
                v{{ item.version }}
                <small v-if="item.version === versions[0].version">
                  最新
                </small>
              </button>
            </div>

            <p v-else class="muted">
              该旅行项目暂时没有已保存的 AI 行程。
            </p>
          </div>

          <div v-if="detailLoading" class="empty-box">
            正在读取行程版本详情...
          </div>

          <template v-else-if="itineraryDetail">
            <div class="summary-grid">
              <div>
                <span>当前版本</span>
                <strong>
                  v{{ itineraryDetail.version }}
                </strong>
              </div>

              <div>
                <span>行程天数</span>
                <strong>
                  {{ itineraryDetail.itinerary?.length || 0 }}
                </strong>
              </div>

              <div>
                <span>质量评分</span>
                <strong>
                  {{ itineraryDetail.quality_score ?? '' }}
                </strong>
              </div>

              <div>
                <span>交通校验</span>
                <strong
                  :class="{
                    success:
                      itineraryDetail.route_validation_passed === true
                  }"
                >
                  {{
                    itineraryDetail.route_validation_passed
                      ? '已通过'
                      : '待完善'
                  }}
                </strong>
              </div>
            </div>

            <div class="itinerary-heading">
              <h3>每日行程安排</h3>
              <span>
                {{ itineraryDetail.status }}
              </span>
            </div>

            <div
              v-for="day in itineraryDetail.itinerary || []"
              :key="day.day"
              class="day-card"
            >
              <div class="day-header">
                <span class="day-number">
                  DAY {{ String(day.day).padStart(2, '0') }}
                </span>
                <div>
                  <h3>第 {{ day.day }} 天  {{ day.theme }}</h3>
                  <p>{{ formatDate(day.date) }}</p>
                </div>
              </div>

              <div
                v-for="(activity, index) in day.activities || []"
                :key="index"
                class="activity-row"
              >
                <div class="activity-time">
                  {{ formatTime(activity.start_time) }}
                  
                  {{ formatTime(activity.end_time) }}
                </div>

                <div class="activity-content">
                  <strong>{{ activity.place_name }}</strong>
                  <p v-if="activity.description">
                    {{ activity.description }}
                  </p>
                </div>
              </div>
            </div>

            <div
              v-if="itineraryDetail.route_warnings?.length"
              class="warning-box"
            >
              <strong>交通提醒</strong>
              <p
                v-for="(warning, index) in itineraryDetail.route_warnings"
                :key="index"
              >
                {{ warning }}
              </p>
            </div>
          </template>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.trips-page {
  display: grid;
  gap: 22px;
}

.page-heading,
.detail-heading,
.version-header,
.itinerary-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.page-eyebrow {
  color: #4c82ee;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.5px;
}

.page-heading h2,
.detail-heading h2 {
  margin: 9px 0;
  font-size: 23px;
  color: #182d4d;
}

.page-heading p,
.detail-heading p,
.muted {
  color: #91a0b4;
  font-size: 12px;
  margin: 0;
}

.refresh-button {
  border: 1px solid #dce6f5;
  background: white;
  color: #477ce5;
  padding: 10px 17px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 700;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 16px;
}

.project-card {
  text-align: left;
  background: #fff;
  border: 1px solid #e7edf7;
  border-radius: 15px;
  padding: 24px;
  min-height: 180px;
}

.project-card.selected {
  border-color: #4384f8;
  box-shadow: 0 0 0 3px #4384f812;
}

.project-top,
.project-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-tag {
  background: #eaf3ff;
  color: #4781ed;
  font-size: 11px;
  font-weight: 700;
  border-radius: 7px;
  padding: 7px 10px;
}

.project-id {
  color: #a6b1c2;
  font-size: 11px;
}

.project-card h3 {
  font-size: 20px;
  margin: 19px 0 8px;
  color: #1b3050;
}

.project-card p {
  margin: 0;
  color: #8b9bb0;
  font-size: 12px;
}

.project-bottom {
  padding-top: 20px;
  font-size: 11px;
  color: #5d86d6;
}

.detail-panel {
  background: white;
  border: 1px solid #e8eef7;
  border-radius: 16px;
  padding: 27px;
}

.version-section {
  border-top: 1px solid #edf1f7;
  margin-top: 23px;
  padding-top: 22px;
}

.version-header h3,
.itinerary-heading h3 {
  font-size: 15px;
  margin: 0;
}

.version-header span,
.itinerary-heading span {
  font-size: 11px;
  color: #97a5b8;
}

.version-buttons {
  margin-top: 15px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.version-buttons button {
  border: 1px solid #dfe8f7;
  background: white;
  color: #5c7fbe;
  padding: 10px 17px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 700;
}

.version-buttons button.active {
  background: #3e7df1;
  color: #fff;
  border-color: #3e7df1;
}

.version-buttons small {
  margin-left: 7px;
  font-size: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 13px;
  margin: 24px 0;
}

.summary-grid > div {
  background: #f5f8fe;
  padding: 17px;
  border-radius: 11px;
}

.summary-grid span {
  color: #91a0b5;
  display: block;
  font-size: 11px;
}

.summary-grid strong {
  color: #233b60;
  display: block;
  margin-top: 9px;
  font-size: 22px;
}

.summary-grid strong.success {
  color: #25a67b;
  font-size: 17px;
}

.itinerary-heading {
  padding: 8px 0 15px;
}

.day-card {
  border: 1px solid #eaf0f8;
  border-radius: 12px;
  margin-bottom: 14px;
  overflow: hidden;
}

.day-header {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #f7faff;
  padding: 18px 20px;
}

.day-number {
  font-size: 11px;
  color: #4d80df;
  font-weight: 800;
}

.day-header h3 {
  font-size: 14px;
  margin: 0 0 6px;
}

.day-header p {
  font-size: 11px;
  color: #9aa7ba;
  margin: 0;
}

.activity-row {
  padding: 18px 20px;
  display: flex;
  gap: 28px;
  border-top: 1px solid #f0f4f9;
}

.activity-time {
  min-width: 135px;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: #467de9;
}

.activity-content strong {
  font-size: 13px;
  color: #203858;
}

.activity-content p {
  color: #8c9db3;
  font-size: 11px;
  line-height: 1.7;
  margin: 7px 0 0;
}

.empty-box {
  background: white;
  border: 1px solid #e8eef7;
  border-radius: 13px;
  padding: 32px;
  color: #90a0b4;
  text-align: center;
  font-size: 13px;
}

.error-box,
.warning-box {
  background: #fff4ee;
  color: #b97544;
  padding: 15px;
  border-radius: 10px;
  font-size: 12px;
}

.warning-box p {
  margin-bottom: 0;
}

@media (max-width: 700px) {
  .detail-panel { padding: 16px; }
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
  .activity-row { display: block; }
  .activity-content { margin-top: 10px; }
  .page-heading { align-items: flex-start; }
}
.trip-planned {
  color: #19a879;
  font-weight: 700;
}
</style>
