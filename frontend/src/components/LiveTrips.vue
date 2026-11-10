<script setup>
import { onMounted, ref } from 'vue'
import {
  getTrips,
  getItineraryVersions,
  getItineraryDetail,
} from '../api/client'

const loading = ref(true)
const error = ref('')
const trips = ref([])
const versions = ref([])
const selectedTripId = ref(null)
const selectedVersion = ref(null)
const detail = ref(null)
const detailLoading = ref(false)

function normalizeTrips(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.trips)) return data.trips
  if (Array.isArray(data?.items)) return data.items
  if (Array.isArray(data?.data)) return data.data
  if (Array.isArray(data?.data?.trips)) return data.data.trips
  throw new Error('旅行列表响应格式需要进一步适配')
}

async function loadDetail(version) {
  if (selectedTripId.value == null) return

  detailLoading.value = true
  error.value = ''

  try {
    const result = await getItineraryDetail(
      selectedTripId.value,
      version,
    )
    detail.value = result
    selectedVersion.value = version
  } catch (err) {
    detail.value = null
    error.value = err.message
  } finally {
    detailLoading.value = false
  }
}

async function loadTrip(tripId) {
  selectedTripId.value = tripId
  selectedVersion.value = null
  versions.value = []
  detail.value = null
  error.value = ''

  try {
    const result = await getItineraryVersions(tripId)
    versions.value = Array.isArray(result?.versions)
      ? result.versions
      : []

    if (versions.value.length > 0) {
      await loadDetail(versions.value[0].version)
    }
  } catch (err) {
    error.value = err.message
  }
}

async function refresh() {
  loading.value = true
  error.value = ''

  try {
    const result = await getTrips()
    trips.value = normalizeTrips(result)

    if (trips.value.length > 0) {
      await loadTrip(trips.value[0].id)
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <section class="live-panel">
    <div class="live-heading">
      <div>
        <span class="live-eyebrow">LIVE DATABASE</span>
        <h2>真实旅行数据</h2>
        <p>通过 FastAPI JWT 接口实时读取 MySQL</p>
      </div>
      <button class="live-refresh" @click="refresh">
        刷新数据
      </button>
    </div>

    <p v-if="loading" class="live-message">
      正在读取旅行项目和历史版本...
    </p>

    <p v-if="error" class="live-error">
      {{ error }}
    </p>

    <template v-if="!loading">
      <div class="live-stats">
        <div>
          <span>旅行项目</span>
          <strong>{{ trips.length }}</strong>
        </div>
        <div>
          <span>历史版本</span>
          <strong>{{ versions.length }}</strong>
        </div>
        <div>
          <span>最新质量评分</span>
          <strong>{{ detail?.quality_score ?? '' }}</strong>
        </div>
        <div>
          <span>规划天数</span>
          <strong>{{ detail?.itinerary?.length ?? '' }}</strong>
        </div>
      </div>

      <div v-if="trips.length" class="live-trip-list">
        <button
          v-for="trip in trips"
          :key="trip.id"
          class="live-trip-button"
          :class="{ chosen: selectedTripId === trip.id }"
          @click="loadTrip(trip.id)"
        >
          {{ trip.title }}  {{ trip.destination }}
        </button>
      </div>

      <p v-else class="live-message">
        当前账号暂无旅行项目。
      </p>

      <div v-if="versions.length" class="live-versions">
        <span>历史版本：</span>
        <button
          v-for="item in versions"
          :key="item.version"
          :class="{ chosen: selectedVersion === item.version }"
          @click="loadDetail(item.version)"
        >
          v{{ item.version }}
        </button>
      </div>

      <p v-if="detailLoading" class="live-message">
        正在读取行程详情...
      </p>

      <div v-if="detail" class="live-itinerary">
        <div class="live-summary">
          <strong>版本 {{ detail.version }}</strong>
          <span>状态：{{ detail.status }}</span>
          <span>交通校验：{{
            detail.route_validation_passed === true
              ? '通过'
              : '未完全通过'
          }}</span>
        </div>

        <div
          v-for="day in detail.itinerary || []"
          :key="day.day"
          class="live-day"
        >
          <h3>第 {{ day.day }} 天  {{ day.date }}</h3>
          <p>{{ day.theme }}</p>
          <div
            v-for="(item, index) in day.activities || []"
            :key="index"
            class="live-activity"
          >
            <span>{{ item.start_time }}{{ item.end_time }}</span>
            <strong>{{ item.place_name }}</strong>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
