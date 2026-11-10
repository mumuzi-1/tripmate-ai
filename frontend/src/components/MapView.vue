<script setup>
import AmapCanvas from './AmapCanvas.vue'
import { ref, onMounted } from 'vue'
import { getTrips, getItineraryVersions } from '../api/client'
import { apiRequest } from '../api/client'

const trips = ref([])
const selectedTripId = ref('')
const versions = ref([])
const selectedVersion = ref('')
const mapData = ref(null)
const loading = ref(false)
const error = ref('')

function normalizeTrips(value) {
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.trips)) return value.trips
  if (Array.isArray(value?.items)) return value.items
  if (Array.isArray(value?.data?.trips)) return value.data.trips
  if (Array.isArray(value?.data)) return value.data
  throw new Error('Cannot recognize trips response')
}

function transportLabel(mode) {
  const names = {
    walking: '步行',
    public_transport: '公共交通',
    driving: '驾车',
    cycling: '骑行',
  }
  return names[mode] || mode || '未知'
}

async function loadMapData() {
  if (!selectedTripId.value || !selectedVersion.value) {
    mapData.value = null
    return
  }

  loading.value = true
  error.value = ''
  mapData.value = null

  try {
    mapData.value = await apiRequest(
      `/trips/${Number(selectedTripId.value)}/map-data?version=${Number(selectedVersion.value)}`
    )
  } catch (err) {
    error.value = err.message || '地图数据读取失败'
  } finally {
    loading.value = false
  }
}

async function loadVersions() {
  versions.value = []
  selectedVersion.value = ''
  mapData.value = null
  error.value = ''

  if (!selectedTripId.value) return

  loading.value = true
  try {
    const response = await getItineraryVersions(
      Number(selectedTripId.value)
    )

    versions.value = Array.isArray(response?.versions)
      ? [...response.versions].sort((a, b) => b.version - a.version)
      : []

    if (versions.value.length) {
      selectedVersion.value = String(versions.value[0].version)
    }
  } catch (err) {
    error.value = err.message || '版本读取失败'
  } finally {
    loading.value = false
  }

  if (selectedVersion.value) await loadMapData()
}

async function initialize() {
  loading.value = true
  error.value = ''

  try {
    trips.value = normalizeTrips(await getTrips())
    if (trips.value.length) {
      selectedTripId.value = String(trips.value[0].id)
    }
  } catch (err) {
    error.value = err.message || '旅行列表读取失败'
  } finally {
    loading.value = false
  }

  if (selectedTripId.value) await loadVersions()
}

onMounted(initialize)
</script>

<template>
  <div class="map-page">
    <header class="map-header">
      <div>
        <span class="map-eyebrow">MAP & ROUTES</span>
        <h2>地图与路线</h2>
        <p>查看真实保存的行程景点与交通路线。</p>
      </div>
      <button class="map-refresh" :disabled="loading" @click="initialize">
        刷新数据
      </button>
    </header>

    <section class="map-panel">
      <div class="map-selectors">
        <label>
          <span>选择旅行项目</span>
          <select v-model="selectedTripId" @change="loadVersions">
            <option value="">请选择项目</option>
            <option
              v-for="trip in trips"
              :key="trip.id"
              :value="String(trip.id)"
            >
              #{{ trip.id }}  {{ trip.title }}
            </option>
          </select>
        </label>

        <label>
          <span>选择行程版本</span>
          <select
            v-model="selectedVersion"
            :disabled="!versions.length"
            @change="loadMapData"
          >
            <option v-if="!versions.length" value="">
              暂无历史版本
            </option>
            <option
              v-for="item in versions"
              :key="item.version"
              :value="String(item.version)"
            >
              v{{ item.version }}
            </option>
          </select>
        </label>
      </div>

      <div v-if="error" class="map-error">{{ error }}</div>
      <p v-if="loading" class="map-muted">正在读取地图数据...</p>

      <template v-if="mapData && !loading">
        <div class="map-stats">
          <div><span>旅行目的地</span><strong>{{ mapData.destination }}</strong></div>
          <div><span>行程版本</span><strong>v{{ mapData.version }}</strong></div>
          <div><span>旅行景点</span><strong>{{ mapData.total_places }}</strong></div>
          <div><span>交通路线</span><strong>{{ mapData.total_routes }}</strong></div>
        </div>

        <div class="map-notice">
          <strong>地图坐标状态</strong>
          <p v-if="!mapData.coordinate_complete">
            当前行程尚未保存完整景点坐标。以下为数据库中的真实游览顺序与交通数据，未绘制虚构地图路线。
          </p>
          <p v-else>
            当前景点坐标齐全，后续可以接入高德地图可视化。
          </p>
        </div>

        <AmapCanvas :places="mapData.places" :routes="mapData.routes || []" :transit-alternative="mapData.transit_alternative || null" />

        <h3 class="map-section-title">每日景点安排</h3>

        <div class="map-days">
          <section
            v-for="(places, dayIndex) in [...new Set(mapData.places.map(item => item.day))].map(day => mapData.places.filter(item => item.day === day))"
            :key="dayIndex"
            class="map-day"
          >
            <h4>第 {{ places[0]?.day }} 天  {{ places[0]?.date }}</h4>
            <div v-for="place in places" :key="place.sequence" class="map-place">
              <span class="map-place-number">{{ place.sequence }}</span>
              <div>
                <strong>{{ place.name }}</strong>
                <p>{{ place.start_time }}  {{ place.end_time }}</p>
                <small v-if="place.longitude != null && place.latitude != null">
                  {{ place.longitude }}, {{ place.latitude }}
                </small>
                <small v-else>坐标待补充</small>
              </div>
            </div>
          </section>
        </div>

        <h3 class="map-section-title">已保存的交通路线</h3>

        <div v-if="mapData.routes.length" class="map-routes">
          <article v-for="route in mapData.routes" :key="route.index" class="map-route">
            <div class="map-route-heading">
              <strong>{{ route.origin_name }}  {{ route.destination_name }}</strong>
              <span>{{ transportLabel(route.transport_mode) }}</span>
            </div>
            <div class="map-route-details">
              <p>预计耗时：<strong>{{ route.duration_min ?? '' }} 分钟</strong></p>
              <p v-if="route.distance_m != null">
                距离：{{ route.distance_m }} 米
              </p>
              <p v-if="route.walking_distance_m != null">
                步行距离：{{ route.walking_distance_m }} 米
              </p>
              <p>数据来源：{{ route.source || '已保存行程' }}</p>
            </div>
          </article>
        </div>
        <p v-else class="map-muted">当前版本没有已保存的交通路线。</p>

        <div v-if="mapData.route_warnings?.length" class="map-error">
          <strong>路线提醒</strong>
          <p v-for="(warning, i) in mapData.route_warnings" :key="i">
            {{ warning }}
          </p>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.map-page { display: grid; gap: 22px; }
.map-header { display: flex; justify-content: space-between; align-items: center; gap: 20px; }
.map-eyebrow { color: #427ef0; font-size: 11px; font-weight: 800; letter-spacing: 1.6px; }
.map-header h2 { color: #193452; margin: 10px 0; font-size: 25px; }
.map-header p { color: #91a2b9; margin: 0; font-size: 12px; }
.map-refresh { border: 1px solid #dce7f8; background: #fff; color: #387bf1; padding: 11px 18px; border-radius: 9px; cursor: pointer; }
.map-panel { background: white; border: 1px solid #e4ecf8; border-radius: 16px; padding: 26px; }
.map-selectors { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.map-selectors label { display: grid; gap: 10px; }
.map-selectors label span { font-size: 13px; font-weight: 700; color: #355475; }
.map-selectors select { width: 100%; padding: 13px; border-radius: 9px; background: #f8fbff; border: 1px solid #dce6f5; color: #294569; }
.map-stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 13px; margin-top: 26px; }
.map-stats > div { background: #f4f8fe; border-radius: 11px; padding: 18px; }
.map-stats span { display: block; color: #92a0b5; font-size: 12px; }
.map-stats strong { display: block; color: #213f66; font-size: 20px; margin-top: 8px; }
.map-notice { background: #f0f6ff; border-radius: 12px; padding: 18px; margin-top: 22px; color: #486a9b; }
.map-notice strong { font-size: 13px; }
.map-notice p { font-size: 12px; line-height: 1.8; margin-bottom: 0; }
.map-section-title { margin: 30px 0 17px; font-size: 17px; color: #203b60; }
.map-days { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 15px; }
.map-day { border: 1px solid #e7eff9; border-radius: 13px; overflow: hidden; }
.map-day h4 { margin: 0; padding: 16px; background: #f4f8ff; font-size: 13px; color: #254b82; }
.map-place { display: flex; gap: 12px; padding: 16px; border-top: 1px solid #edf2f8; }
.map-place-number { display: grid; place-items: center; flex: 0 0 27px; height: 27px; border-radius: 50%; color: white; background: #417ef0; font-weight: 700; font-size: 12px; }
.map-place strong { color: #263e60; font-size: 13px; }
.map-place p { margin: 7px 0; color: #4f81d5; font-size: 12px; }
.map-place small { color: #9ba9bd; }
.map-routes { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 15px; }
.map-route { border: 1px solid #e5edf8; border-radius: 12px; padding: 20px; }
.map-route-heading { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; align-items: center; }
.map-route-heading strong { font-size: 14px; color: #234165; }
.map-route-heading span { background: #eaf3ff; color: #367bec; border-radius: 8px; padding: 7px 11px; font-size: 11px; }
.map-route-details p { color: #788ea9; font-size: 12px; }
.map-route-details strong { color: #1f3d61; }
.map-error { padding: 14px; background: #fff1ed; color: #af5543; border-radius: 10px; margin-top: 20px; font-size: 12px; }
.map-muted { color: #92a2b8; font-size: 13px; margin-top: 20px; }
@media (max-width: 1050px) {
  .map-days { grid-template-columns: 1fr; }
  .map-routes { grid-template-columns: 1fr; }
}
@media (max-width: 650px) {
  .map-selectors, .map-stats { grid-template-columns: 1fr 1fr; }
  .map-panel { padding: 16px; }
  .map-header { display: block; }
}
</style>
