<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  places: { type: Array, default: () => [] },
  routes: { type: Array, default: () => [] },
  transitAlternative: { type: Object, default: null },
})

const container = ref(null)
const selectedDay = ref(0)
const showTransitAlternative = ref(false)
const loading = ref(true)
const error = ref('')

let map = null
let markers = []
let routeLines = []
let transitLines = []
let infoWindow = null
let disposed = false

const validPlaces = computed(() =>
  props.places.filter((p) =>
    p.longitude != null &&
    p.latitude != null &&
    Number.isFinite(Number(p.longitude)) &&
    Number.isFinite(Number(p.latitude))
  )
)

const days = computed(() =>
  [...new Set(validPlaces.value.map((p) => Number(p.day)))]
    .sort((a, b) => a - b)
)

function loadAmap() {
  if (window.AMap?.Map) return Promise.resolve(window.AMap)
  if (window.__tripmateAmapLoading) return window.__tripmateAmapLoading

  const key = import.meta.env.VITE_AMAP_JS_KEY

  if (!key) {
    return Promise.reject(new Error('VITE_AMAP_JS_KEY is missing'))
  }

  window._AMapSecurityConfig = {
    serviceHost: `${window.location.origin}/_AMapService`,
  }

  window.__tripmateAmapLoading = new Promise((resolve, reject) => {
    const callbackName = '__tripmateAmapReady'
    const script = document.createElement('script')

    const timeout = window.setTimeout(() => {
      cleanup()
      reject(new Error('Amap JS API loading timed out'))
    }, 20000)

    function cleanup() {
      window.clearTimeout(timeout)
      delete window[callbackName]
    }

    window[callbackName] = () => {
      cleanup()
      if (window.AMap?.Map) resolve(window.AMap)
      else reject(new Error('AMap SDK initialization failed'))
    }

    script.src =
      `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}` +
      `&callback=${callbackName}`

    script.async = true
    script.onerror = () => {
      cleanup()
      script.remove()
      reject(new Error('Unable to load Amap JS API'))
    }

    document.head.appendChild(script)
  }).catch((err) => {
    window.__tripmateAmapLoading = null
    throw err
  })

  return window.__tripmateAmapLoading
}


function renderMarkers() {
  if (!map || !window.AMap) return

  if (infoWindow) {
    infoWindow.close()
    infoWindow = null
  }

  map.remove(markers)
  markers = []

  const colors = {
    1: '#397cf2',
    2: '#15a487',
    3: '#8b5cf6',
  }

  const sequenceByDay = {}

  const indexedPlaces = validPlaces.value.map((place) => {
    const day = Number(place.day) || 1
    sequenceByDay[day] = (sequenceByDay[day] || 0) + 1
    return {
      ...place,
      displayDay: day,
      displayOrder: sequenceByDay[day],
    }
  })

  const visible = indexedPlaces.filter(
    (place) =>
      selectedDay.value === 0 ||
      place.displayDay === selectedDay.value
  )

  for (const place of visible) {
    const color = colors[place.displayDay] || '#397cf2'

    const content = document.createElement('div')
    content.style.cssText =
      'display:flex;flex-direction:column;align-items:center;' +
      'gap:5px;cursor:pointer;min-width:40px;'

    const bubble = document.createElement('div')
    bubble.textContent = String(place.displayOrder)
    bubble.style.cssText =
      'width:34px;height:34px;border-radius:50%;' +
      'background:' + color + ';color:white;' +
      'font-size:15px;font-weight:700;' +
      'display:flex;align-items:center;justify-content:center;' +
      'border:3px solid white;' +
      'box-shadow:0 3px 12px rgba(20,45,85,.25);'

    const label = document.createElement('div')
    label.textContent = place.name || ''
    label.style.cssText =
      'background:white;border:1px solid #e1e9f5;' +
      'border-radius:7px;padding:4px 8px;' +
      'font-size:12px;color:#17385e;font-weight:600;' +
      'white-space:nowrap;box-shadow:0 2px 8px rgba(20,45,85,.12);'

    // Show all labels when filtering by a single day.
    // Hide labels by default for the complete itinerary.
    label.style.display = selectedDay.value === 0 ? 'none' : 'block'

    content.appendChild(bubble)
    content.appendChild(label)

    const marker = new window.AMap.Marker({
      position: [
        Number(place.longitude),
        Number(place.latitude),
      ],
      content,
      title: place.name,
      anchor: 'bottom-center',
      zIndex: 110,
    })

    marker.on('mouseover', () => {
      label.style.display = 'block'
      marker.setzIndex(200)
    })

    marker.on('mouseout', () => {
      if (selectedDay.value === 0) {
        label.style.display = 'none'
      }
      marker.setzIndex(110)
    })

    marker.on('click', () => {
      const panel = document.createElement('div')
      panel.style.cssText =
        'min-width:190px;padding:12px;font-family:sans-serif;'

      const heading = document.createElement('div')
      heading.textContent = place.name || ''
      heading.style.cssText =
        'font-size:16px;font-weight:700;color:#17385e;'

      const dayLine = document.createElement('div')
      dayLine.textContent =
        '\u7b2c ' + place.displayDay +
        ' \u5929 \u00b7 \u7b2c ' +
        place.displayOrder + ' \u7ad9'
      dayLine.style.cssText =
        'font-size:12px;color:' + color + ';margin-top:8px;'

      const timeLine = document.createElement('div')
      timeLine.textContent =
        '\u6e38\u89c8\u65f6\u95f4\uff1a' +
        (place.start_time || '--:--') + ' - ' +
        (place.end_time || '--:--')
      timeLine.style.cssText =
        'font-size:12px;color:#61748e;margin-top:7px;'

      panel.appendChild(heading)
      panel.appendChild(dayLine)
      panel.appendChild(timeLine)

      if (infoWindow) infoWindow.close()

      infoWindow = new window.AMap.InfoWindow({
        content: panel,
        offset: new window.AMap.Pixel(0, -40),
      })

      infoWindow.open(map, marker.getPosition())
    })

    markers.push(marker)
  }

  if (markers.length) {
    map.add(markers)
    map.setFitView(markers, false, [110, 110, 110, 110])
  }
  renderWalkingRoutes()
  renderTransitAlternative()

}


/* TRIPMATE_WALKING_POLYLINE_V1 */
function renderWalkingRoutes() {
  if (!map || !window.AMap) return

  if (routeLines.length) {
    map.remove(routeLines)
    routeLines = []
  }

  const walkingRoutes = (props.routes || []).filter(
    (route) =>
      route.transport_mode === 'walking' &&
      route.geometry_source === 'amap_cache' &&
      Array.isArray(route.polyline) &&
      route.polyline.length >= 2
  )

  for (const route of walkingRoutes) {
    const origin = validPlaces.value.find(
      (p) => p.name === route.origin_name
    )

    const destination = validPlaces.value.find(
      (p) => p.name === route.destination_name
    )

    if (!origin || !destination) continue

    const routeDay = Number(origin.day)

    if (routeDay !== Number(destination.day)) continue

    if (
      selectedDay.value !== 0 &&
      selectedDay.value !== routeDay
    ) continue

    const path = route.polyline.map(
      (point) => [Number(point[0]), Number(point[1])]
    )

    if (!path.every(
      ([lon, lat]) =>
        Number.isFinite(lon) && Number.isFinite(lat)
    )) continue

    const line = new window.AMap.Polyline({
      path,
      strokeColor: '#8b5cf6',
      strokeWeight: 7,
      strokeOpacity: 0.9,
      strokeStyle: 'solid',
      lineJoin: 'round',
      lineCap: 'round',
      zIndex: 75,
    })

    map.add(line)
    routeLines.push(line)
  }
}


/* TRIPMATE_TRANSIT_OVERLAY_V1 */
function renderTransitAlternative() {
  if (!map || !window.AMap) return

  if (transitLines.length) {
    map.remove(transitLines)
    transitLines = []
  }

  const alternative = props.transitAlternative

  if (
    !showTransitAlternative.value ||
    !alternative ||
    alternative.route_type !== 'alternative' ||
    !Array.isArray(alternative.segments)
  ) return

  // The Lingyin Temple to Xixi Wetland route belongs to Day 2.
  // All-days mode also allows displaying this overlay.
  const origin = validPlaces.value.find(
    (place) => place.name === alternative.origin_name
  )
  const destination = validPlaces.value.find(
    (place) => place.name === alternative.destination_name
  )

  if (!origin || !destination) return

  const routeDay = Number(origin.day)

  if (
    !routeDay ||
    Number(destination.day) !== routeDay ||
    (selectedDay.value !== 0 && selectedDay.value !== routeDay)
  ) return

  for (const segment of alternative.segments) {
    if (!Array.isArray(segment.polyline)) continue
    if (segment.polyline.length < 2) continue

    const path = segment.polyline.map((point) => [
      Number(point[0]),
      Number(point[1]),
    ])

    if (!path.every(([lon, lat]) =>
      Number.isFinite(lon) && Number.isFinite(lat)
    )) continue

    const mode = segment.mode

    if (!['walking', 'bus', 'subway'].includes(mode)) continue

    const color = mode === 'subway'
      ? '#2563eb'
      : mode === 'bus'
        ? '#16a34a'
        : '#f59e0b'

    const line = new window.AMap.Polyline({
      path,
      strokeColor: color,
      strokeWeight: mode === 'walking' ? 4 : 7,
      strokeOpacity: 0.9,
      strokeStyle: mode === 'walking' ? 'dashed' : 'solid',
      strokeDasharray: mode === 'walking' ? [8, 6] : undefined,
      lineJoin: 'round',
      lineCap: 'round',
      zIndex: 60,
    })

    map.add(line)
    transitLines.push(line)
  }
  // TRIPMATE_TRANSIT_FIT_V1
  // Fit both POI markers and real transit segments into view.
  if (transitLines.length && markers.length) {
    map.setFitView(
      [...markers, ...transitLines],
      false,
      [100, 110, 100, 110]
    )
  }

}

async function initialize() {
  if (!container.value) return

  try {
    loading.value = true
    error.value = ''

    const AMap = await loadAmap()
    if (disposed || !container.value) return

    await nextTick()

    map = new AMap.Map(container.value, {
      zoom: 12,
      center: [120.15, 30.25],
      viewMode: '2D',
      resizeEnable: true,
    })

    renderMarkers()
  } catch (err) {
    if (!disposed) error.value = err.message || 'Map loading failed'
  } finally {
    if (!disposed) loading.value = false
  }
}

watch([validPlaces, selectedDay, () => props.routes, () => props.transitAlternative], () => {
  renderMarkers()
})

watch(showTransitAlternative, () => {
  renderTransitAlternative()

  if (!showTransitAlternative.value && map && markers.length) {
    map.setFitView(markers, false, [100, 110, 100, 110])
  }
})

watch(() => props.transitAlternative, () => {
  showTransitAlternative.value = false
})

onMounted(initialize)

onUnmounted(() => {
  disposed = true
  if (infoWindow) infoWindow.close()
  if (map && routeLines.length) map.remove(routeLines)
  routeLines = []
  if (map && transitLines.length) map.remove(transitLines)
  transitLines = []
  if (map) map.destroy()
  map = null
  markers = []
})
</script>

<template>
  <section class="amap-card">
    <div class="amap-heading">
      <div>
        <h3>交互式旅行地图</h3>
        <p>高德地图·已核实景点</p>
      </div>
      
      <button
        v-if="props.transitAlternative"
        class="transit-toggle"
        :class="{ active: showTransitAlternative }"
        :aria-pressed="showTransitAlternative"
        @click="showTransitAlternative = !showTransitAlternative"
      >
        {{ showTransitAlternative ? '隐藏高德备选路线' : '显示高德备选路线' }}
      </button>
      <div class="day-buttons">
        <button
          :class="{ active: selectedDay === 0 }"
          @click="selectedDay = 0"
        >全部日期</button>
        <button
          v-for="day in days"
          :key="day"
          :class="{ active: selectedDay === day }"
          @click="selectedDay = day"
        >第 {{ day }} 天</button>
      </div>
    </div>

    
    
    
    
    <!-- TRIPMATE_TRANSIT_DETAILS_V1 -->
    <div
      v-if="props.transitAlternative && showTransitAlternative"
      class="transit-details"
    >
      <div class="transit-details-top">
        <div>
          <h3>
            {{ props.transitAlternative.origin_name }}
            
            {{ props.transitAlternative.destination_name }}
          </h3>
          <p>高德地图·已缓存的交通轨迹</p>
        </div>
        <span class="transit-details-badge">
          高德备选路线（非原行程）
        </span>
      </div>

      <div class="transit-details-stats">
        <div class="transit-stat">
          <small>原行程预计耗时</small>
          <strong>
            {{ props.transitAlternative.saved_duration_min }}
            分钟
          </strong>
        </div>
        <div class="transit-stat">
          <small>备选路线预计耗时</small>
          <strong>
            {{ props.transitAlternative.alternative_duration_min }}
            分钟
          </strong>
        </div>
      </div>

      <div class="transit-details-legend">
        <div
          v-for="(line, index) in (props.transitAlternative.line_names || [])"
          :key="'line-' + index"
          class="transit-legend-item"
        >
          <span class="transit-legend-line subway"></span>
          <span>{{ line }}</span>
        </div>

        <div
          v-if="props.transitAlternative.segments?.some(
            item => item.mode === 'walking'
          )"
          class="transit-legend-item"
        >
          <span class="transit-legend-line walking"></span>
          <span>步行接驳</span>
          <span class="transit-legend-count">
            {{ props.transitAlternative.segments.filter(
              item => item.mode === 'walking'
            ).length }} 段
          </span>
        </div>
      </div>

      <p class="transit-details-note">
        此备选方案与原行程不同，
        不包含原行程中的 121 路公交。
        具体上下车站点尚未保存。
      </p>
    </div>

    <div class="amap-frame">
      <div ref="container" class="amap-container"></div>
      <div v-if="loading" class="amap-overlay">正在加载地图...</div>
      <div v-if="error" class="amap-overlay amap-error">{{ error }}</div>
    </div>

    <div class="amap-footer">
      {{ validPlaces.length }} 个已核实景点
      <span>地图标记为景点位置，不代表实际道路路线。</span>
    </div>
  </section>
</template>

<style scoped>
.amap-card {
  margin: 24px 0;
  border: 1px solid #e4ecf8;
  border-radius: 16px;
  overflow: hidden;
  background: white;
}
.amap-heading {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.amap-heading h3 {
  color: #193452;
  margin: 0 0 6px;
  font-size: 18px;
}
.amap-heading p {
  color: #91a2b9;
  font-size: 12px;
  margin: 0;
}
.day-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.day-buttons button {
  padding: 9px 12px;
  border: 1px solid #dce6f5;
  background: #f6f9ff;
  color: #42638b;
  border-radius: 9px;
  cursor: pointer;
}
.day-buttons button.active {
  background: #397cf2;
  color: white;
  border-color: #397cf2;
}
.amap-frame {
  height: 440px;
  position: relative;
  background: #f2f6fc;
}
.amap-container {
  width: 100%;
  height: 100%;
}
.amap-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(248,250,255,.92);
  color: #51709b;
}
.amap-error { color: #c14a4a; }
.amap-footer {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 20px;
  color: #8296b2;
  font-size: 12px;
}
@media (max-width: 700px) {
  .amap-frame { height: 340px; }
  .amap-footer { flex-direction: column; }
}
</style>

<style scoped>
.day-buttons button {
  font-size: 13px;
  font-weight: 500;
  transition: background-color .2s, border-color .2s;
}
.amap-heading {
  min-height: 82px;
}
</style>

<style scoped>
.transit-toggle {
  padding: 9px 13px;
  border: 1px solid #bfd3f8;
  background: #eff5ff;
  color: #2764b7;
  border-radius: 9px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.transit-toggle.active {
  color: #fff;
  background: #2563eb;
  border-color: #2563eb;
}
.transit-alternative-notice {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px 20px;
  background: #f0f6ff;
  border-top: 1px solid #dfebff;
  color: #476488;
  font-size: 12px;
}
.transit-alternative-notice strong {
  color: #1d4f91;
}
</style>

<style scoped>
.transit-details {
  padding: 20px;
  border-top: 1px solid #dfe9f8;
  background: #f5f8fe;
}
.transit-details-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
}
.transit-details-top h3 {
  margin: 0 0 7px;
  font-size: 16px;
  color: #183556;
}
.transit-details-top p {
  margin: 0;
  font-size: 12px;
  color: #8497b1;
}
.transit-details-badge {
  background: #e4eeff;
  color: #2865ba;
  font-size: 12px;
  padding: 7px 11px;
  border-radius: 8px;
}
.transit-details-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}
.transit-stat {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 14px 16px;
  background: white;
  border: 1px solid #e1e9f5;
  border-radius: 10px;
}
.transit-stat small {
  color: #8395ac;
  font-size: 12px;
}
.transit-stat strong {
  color: #1a365a;
  font-size: 20px;
}
.transit-details-legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 22px;
  margin-top: 18px;
}
.transit-legend-item {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #29476e;
  font-size: 13px;
}
.transit-legend-line {
  display: inline-block;
  width: 34px;
  height: 0;
  border-top: 5px solid;
  border-radius: 3px;
}
.transit-legend-line.subway {
  border-color: #2563eb;
}
.transit-legend-line.walking {
  border-color: #f59e0b;
  border-top-style: dashed;
}
.transit-legend-count {
  color: #8b9bb1;
  font-size: 12px;
}
.transit-details-note {
  margin: 16px 0 0;
  font-size: 12px;
  line-height: 1.7;
  color: #788ba5;
}
@media (max-width: 650px) {
  .transit-details-stats {
    grid-template-columns: 1fr;
  }
}
</style>
