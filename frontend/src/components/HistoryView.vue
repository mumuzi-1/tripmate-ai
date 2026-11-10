<script setup>
import { onMounted, ref } from 'vue'
import {
  getTrips,
  getItineraryVersions,
  getItineraryDetail,
} from '../api/client'

const trips = ref([])
const tripId = ref('')
const versions = ref([])
const version = ref(null)
const detail = ref(null)
const loading = ref(false)
const detailLoading = ref(false)
const error = ref('')

function normalizeTrips(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.trips)) return data.trips
  if (Array.isArray(data?.items)) return data.items
  if (Array.isArray(data?.data)) return data.data
  if (Array.isArray(data?.data?.trips)) return data.data.trips
  throw new Error('无法识别旅行项目列表')
}

async function loadVersion(selectedVersion) {
  if (!tripId.value) return
  detailLoading.value = true
  error.value = ''
  detail.value = null

  try {
    const result = await getItineraryDetail(
      Number(tripId.value),
      selectedVersion
    )
    detail.value = result
    version.value = selectedVersion
  } catch (err) {
    error.value = err.message || '历史版本详情读取失败'
  } finally {
    detailLoading.value = false
  }
}

async function loadVersions() {
  error.value = ''
  versions.value = []
  detail.value = null
  version.value = null
  if (!tripId.value) return

  loading.value = true
  try {
    const result = await getItineraryVersions(Number(tripId.value))
    versions.value = Array.isArray(result?.versions)
      ? [...result.versions].sort((a, b) => b.version - a.version)
      : []

    if (versions.value.length > 0) {
      await loadVersion(versions.value[0].version)
    }
  } catch (err) {
    error.value = err.message || '历史版本读取失败'
  } finally {
    loading.value = false
  }
}

async function initialize() {
  loading.value = true
  error.value = ''
  try {
    trips.value = normalizeTrips(await getTrips())
    if (trips.value.length) {
      tripId.value = String(trips.value[0].id)
    }
  } catch (err) {
    error.value = err.message || '旅行项目读取失败'
  } finally {
    loading.value = false
  }
  if (tripId.value) await loadVersions()
}

function time(value) {
  return String(value || '').slice(0, 5)
}

onMounted(initialize)
</script>

<template>
  <div class="history-view">
    <header class="hv-header">
      <div>
        <span class="hv-eyebrow">TRAVEL HISTORY</span>
        <h2>历史规划版本</h2>
        <p>查看 MySQL 中保存的 AI 旅行规划记录。</p>
      </div>
      <button class="hv-btn" @click="initialize" :disabled="loading">
        刷新数据
      </button>
    </header>

    <section class="hv-panel">
      <label class="hv-label" for="hv-trip">选择旅行项目</label>
      <select id="hv-trip" v-model="tripId" @change="loadVersions">
        <option value="">请选择旅行项目</option>
        <option
          v-for="trip in trips"
          :key="trip.id"
          :value="String(trip.id)"
        >
          #{{ trip.id }}  {{ trip.title }}  {{ trip.destination }}
        </option>
      </select>

      <p v-if="error" class="hv-error">{{ error }}</p>
      <p v-if="loading" class="hv-muted">正在读取旅行数据...</p>

      <template v-else>
        <div class="hv-section-title">
          <h3>已保存的历史版本</h3>
          <span>共 {{ versions.length }} 个版本</span>
        </div>

        <div v-if="versions.length" class="hv-version-list">
          <button
            v-for="item in versions"
            :key="item.version"
            :class="{ active: version === item.version }"
            :disabled="detailLoading"
            @click="loadVersion(item.version)"
          >
            <strong>v{{ item.version }}</strong>
            <span>质量评分 {{ item.quality_score ?? '' }}</span>
            <small>{{ item.status }}</small>
          </button>
        </div>

        <p v-else-if="tripId" class="hv-empty">
          当前旅行项目尚未保存 AI 行程。
        </p>

        <p v-if="detailLoading" class="hv-muted">
          正在读取版本详情...
        </p>

        <template v-if="detail && !detailLoading">
          <div class="hv-metrics">
            <div>
              <span>行程版本</span>
              <strong>v{{ detail.version }}</strong>
            </div>
            <div>
              <span>行程天数</span>
              <strong>{{ detail.itinerary?.length ?? 0 }}</strong>
            </div>
            <div>
              <span>质量评分</span>
              <strong>{{ detail.quality_score ?? '' }}</strong>
            </div>
            <div>
              <span>交通校验</span>
              <strong>
                {{ detail.route_validation_passed ? '已通过' : '待完善' }}
              </strong>
            </div>
          </div>

          <div
            v-for="day in detail.itinerary || []"
            :key="day.day"
            class="hv-day"
          >
            <div class="hv-day-heading">
              <span>DAY {{ String(day.day).padStart(2, '0') }}</span>
              <div>
                <h3>第 {{ day.day }} 天  {{ day.theme }}</h3>
                <p>{{ day.date }}</p>
              </div>
            </div>

            <div
              v-for="(item, index) in day.activities || []"
              :key="index"
              class="hv-activity"
            >
              <span>{{ time(item.start_time) }}  {{ time(item.end_time) }}</span>
              <div>
                <strong>{{ item.place_name }}</strong>
                <p v-if="item.description">{{ item.description }}</p>
              </div>
            </div>
          </div>

          <div v-if="detail.route_warnings?.length" class="hv-warning">
            <strong>交通提醒</strong>
            <p v-for="(warning, index) in detail.route_warnings" :key="index">
              {{ warning }}
            </p>
          </div>
        </template>
      </template>
    </section>
  </div>
</template>

<style scoped>
.history-view { display: grid; gap: 22px; }
.hv-header { display: flex; justify-content: space-between; gap: 16px; align-items: center; }
.hv-eyebrow { color: #4482f2; font-size: 11px; font-weight: 800; letter-spacing: 1.6px; }
.hv-header h2 { color: #182d4d; font-size: 25px; margin: 10px 0; }
.hv-header p { color: #91a1b6; font-size: 12px; margin: 0; }
.hv-panel { padding: 26px; border: 1px solid #e6edf8; background: #fff; border-radius: 16px; }
.hv-btn { background: white; color: #407ee8; border: 1px solid #dbe6f7; border-radius: 9px; padding: 11px 16px; cursor: pointer; }
.hv-label { display: block; font-size: 13px; color: #48617f; font-weight: 700; margin-bottom: 12px; }
.hv-panel select { width: 100%; max-width: 520px; border: 1px solid #dce6f4; padding: 13px; border-radius: 9px; background: #f8fbff; color: #294467; }
.hv-section-title { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #eef2f8; margin-top: 25px; padding-top: 20px; gap: 12px; }
.hv-section-title h3 { margin: 0; font-size: 16px; color: #233a58; }
.hv-section-title span { color: #9aa8bd; font-size: 12px; }
.hv-version-list { display: flex; gap: 12px; margin-top: 17px; flex-wrap: wrap; }
.hv-version-list button { display: flex; flex-direction: column; align-items: start; gap: 6px; background: #f6f9ff; border: 1px solid #e5ecf8; border-radius: 11px; padding: 15px 20px; cursor: pointer; color: #355474; }
.hv-version-list button.active { background: #eaf2ff; border-color: #4484f4; }
.hv-version-list button strong { color: #387bf0; font-size: 18px; }
.hv-version-list button span, .hv-version-list button small { color: #8b9bb1; font-size: 11px; }
.hv-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 13px; margin: 25px 0; }
.hv-metrics > div { background: #f5f8fe; border-radius: 11px; padding: 17px; }
.hv-metrics span { display: block; color: #92a0b5; font-size: 11px; }
.hv-metrics strong { display: block; margin-top: 9px; font-size: 22px; color: #1c385d; }
.hv-day { border: 1px solid #e8eff8; border-radius: 12px; overflow: hidden; margin-bottom: 14px; }
.hv-day-heading { display: flex; gap: 17px; align-items: center; background: #f6f9ff; padding: 18px; }
.hv-day-heading > span { color: #4680e8; font-size: 11px; font-weight: 800; }
.hv-day-heading h3 { margin: 0 0 5px; font-size: 14px; }
.hv-day-heading p { margin: 0; color: #9aa8ba; font-size: 11px; }
.hv-activity { display: flex; gap: 24px; padding: 15px 18px; border-top: 1px solid #edf2f9; font-size: 12px; }
.hv-activity > span { color: #4780ea; min-width: 125px; }
.hv-activity strong { color: #223d5e; }
.hv-activity p { margin: 8px 0 0; color: #8f9fb4; line-height: 1.6; }
.hv-error, .hv-warning { background: #fff2ec; color: #b35c41; border-radius: 9px; padding: 14px; font-size: 12px; margin-top: 17px; }
.hv-muted, .hv-empty { color: #91a1b5; font-size: 13px; padding: 20px 0; }
@media (max-width: 720px) {
  .hv-metrics { grid-template-columns: repeat(2, 1fr); }
  .hv-panel { padding: 15px; }
  .hv-activity { display: block; }
  .hv-activity > span { display: block; margin-bottom: 8px; }
}
</style>
