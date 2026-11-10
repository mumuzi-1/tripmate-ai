<script setup>
import { computed, ref, onMounted } from 'vue'
import { apiRequest, getTrips, getTripRequirements, getItineraryVersions, getItineraryDetail } from '../api/client'

const loading = ref(false)
const generating = ref(false)
const error = ref('')
const message = ref('')
const tripId = ref(null)
const existingTrips = ref([])
const selectedExistingId = ref('')
const selectingTrip = ref(false)
const generated = ref(null)
const savedVersions = ref([])
const selectedVersion = ref(null)
const historyLoading = ref(false)

const form = ref({
  title: '杭州三日游',
  destination: '杭州',
  departure_city: '南京',
  start_date: '2027-04-03',
  end_date: '2027-04-05',
  travelers: 2,
  travel_style: 'sightseeing',
  travel_pace: 'moderate',
  transport_preference: 'public_transport',
  accommodation_preference: '经济型酒店',
  daily_start_time: '09:00',
  daily_end_time: '20:00',
  must_visit_places: '西湖、灵隐寺、西溪湿地',
  excluded_places: '',
  preferred_activities: '美食、城市观光',
  special_requirements:
    '希望合理安排每天的景点顺序，减少重复路线，优先选择公共交通。',
})

const canGenerate = computed(
  () => tripId.value !== null && !loading.value && !generating.value
)

function parsePlaces(value) {
  return String(value || '')
    .split(/[,，、;\n；]+/)
    .map(item => item.trim())
    .filter(Boolean)
}

function validateForm() {
  if (!form.value.title.trim()) {
    throw new Error('请输入旅行名称')
  }

  if (!form.value.destination.trim()) {
    throw new Error('请输入旅行目的地')
  }

  if (!form.value.departure_city.trim()) {
    throw new Error('请输入出发城市')
  }

  if (!form.value.start_date || !form.value.end_date) {
    throw new Error('请选择旅行日期')
  }

  if (form.value.end_date < form.value.start_date) {
    throw new Error('结束日期不能早于开始日期')
  }

  if (
    !Number.isInteger(Number(form.value.travelers)) ||
    Number(form.value.travelers) < 1
  ) {
    throw new Error('出行人数必须是正整数')
  }

  if (form.value.daily_end_time <= form.value.daily_start_time) {
    throw new Error('每日结束时间必须晚于开始时间')
  }
}

function buildRequirements() {
  return {
    departure_city: form.value.departure_city.trim(),
    start_date: form.value.start_date,
    end_date: form.value.end_date,
    travelers: Number(form.value.travelers),
    travel_style: form.value.travel_style,
    travel_pace: form.value.travel_pace,
    transport_preference: form.value.transport_preference,
    accommodation_preference:
      form.value.accommodation_preference.trim() || null,
    daily_start_time: `${form.value.daily_start_time}:00`,
    daily_end_time: `${form.value.daily_end_time}:00`,
    must_visit_places: parsePlaces(form.value.must_visit_places),
    excluded_places: parsePlaces(form.value.excluded_places),
    preferred_activities: parsePlaces(form.value.preferred_activities),
    special_requirements:
      form.value.special_requirements.trim() || null,
  }
}

function normalizeTripList(response) {
  if (Array.isArray(response)) return response
  if (Array.isArray(response?.trips)) return response.trips
  if (Array.isArray(response?.items)) return response.items
  if (Array.isArray(response?.data)) return response.data
  if (Array.isArray(response?.data?.trips)) return response.data.trips
  throw new Error('无法识别旅行项目列表')
}

async function refreshExistingTrips() {
  try {
    existingTrips.value = normalizeTripList(await getTrips())
  } catch (err) {
    error.value = `读取已有项目失败：${err.message}`
  }
}

function toCommaText(value) {
  if (Array.isArray(value)) return value.join('、')
  return typeof value === 'string' ? value : ''
}

function toInputTime(value, fallback) {
  return value ? String(value).slice(0, 5) : fallback
}

async function loadSavedVersion(version) {
  if (tripId.value === null) return

  historyLoading.value = true
  error.value = ''

  try {
    generated.value = await getItineraryDetail(
      tripId.value,
      version,
    )
    selectedVersion.value = version
  } catch (err) {
    error.value = `读取历史版本失败：${err.message}`
  } finally {
    historyLoading.value = false
  }
}

async function refreshSavedVersions() {
  if (tripId.value === null) return

  historyLoading.value = true

  try {
    const response = await getItineraryVersions(tripId.value)
    savedVersions.value = Array.isArray(response.versions)
      ? response.versions
      : []

    if (savedVersions.value.length > 0) {
      await loadSavedVersion(savedVersions.value[0].version)
    } else {
      generated.value = null
      selectedVersion.value = null
    }
  } catch (err) {
    error.value = `读取版本列表失败：${err.message}`
  } finally {
    historyLoading.value = false
  }
}
async function loadExistingTrip() {
  if (!selectedExistingId.value) return

  selectingTrip.value = true
  error.value = ''
  message.value = ''

  try {
    const selectedId = Number(selectedExistingId.value)
    const trip = existingTrips.value.find(
      item => Number(item.id) === selectedId
    )

    if (!trip) throw new Error('未找到所选旅行项目')

    const response = await getTripRequirements(selectedId)
    const requirements = response?.data?.departure_city
      ? response.data
      : response

    form.value = {
      ...form.value,
      title: trip.title,
      destination: trip.destination,
      departure_city: requirements.departure_city || '',
      start_date: String(requirements.start_date || '').slice(0, 10),
      end_date: String(requirements.end_date || '').slice(0, 10),
      travelers: requirements.travelers ?? 2,
      travel_style: requirements.travel_style || 'sightseeing',
      travel_pace: requirements.travel_pace || 'moderate',
      transport_preference:
        requirements.transport_preference || 'public_transport',
      accommodation_preference:
        requirements.accommodation_preference || '',
      daily_start_time:
        toInputTime(requirements.daily_start_time, '09:00'),
      daily_end_time:
        toInputTime(requirements.daily_end_time, '20:00'),
      must_visit_places:
        toCommaText(requirements.must_visit_places),
      excluded_places:
        toCommaText(requirements.excluded_places),
      preferred_activities:
        toCommaText(requirements.preferred_activities),
      special_requirements:
        requirements.special_requirements || '',
    }

    tripId.value = selectedId
    generated.value = null
    await refreshSavedVersions()
    message.value = `已加载项目 ${selectedId}，可修改需求或生成新版本`
  } catch (err) {
    selectedExistingId.value = ''
    error.value = `加载旅行项目失败：${err.message}`
  } finally {
    selectingTrip.value = false
  }
}

onMounted(refreshExistingTrips)
async function saveRequirements() {
  loading.value = true
  error.value = ''
  message.value = ''

  try {
    validateForm()

    // 首次保存：先创建旅行项目
    if (tripId.value === null) {
      const trip = await apiRequest('/trips', {
        method: 'POST',
        body: {
          title: form.value.title.trim(),
          destination: form.value.destination.trim(),
        },
      })

      if (!trip?.id) {
        throw new Error('创建旅行项目后未收到项目 ID')
      }

      tripId.value = trip.id
    }

    // 判断该项目是否已有需求
    let exists = false

    try {
      await apiRequest(`/trips/${tripId.value}/requirements`)
      exists = true
    } catch (requestError) {
      if (requestError.status !== 404) {
        throw requestError
      }
    }

    // 已有需求使用 PUT；首次创建使用 POST
    await apiRequest(`/trips/${tripId.value}/requirements`, {
      method: exists ? 'PUT' : 'POST',
      body: buildRequirements(),
    })

    generated.value = null
    message.value = `旅行需求保存成功！项目 ID：${tripId.value}`
  } catch (err) {
    error.value = err.message || '保存失败'
  } finally {
    loading.value = false
  }
}

async function generatePlan() {
  if (!canGenerate.value) return

  // AI_GENERATE_CONFIRM_V1
  const versionCount = savedVersions.value.length

  const confirmationMessage = [
    "确定开始 AI 旅行规划吗？",
    '',
    "当前项目 ID：" + tripId.value,
    "已有历史版本：" + versionCount + "个",
    '',
    versionCount > 0
      ? "本次将请求生成新版本，不会主动删除旧版本。"
      : "本次将生成该项目的第一个行程版本。",
    '',
    "此次操作将调用 Qwen 和高德地图，可能产生 API 费用。",
    "请确认旅行需求已经保存。",
  ].join('\n')

  if (!window.confirm(confirmationMessage)) {
    return
  }

  generating.value = true
  error.value = ''
  message.value = ''

  try {
    const result = await apiRequest(
      `/trips/${tripId.value}/generate`,
      { method: 'POST' },
    )

    generated.value = result
    await refreshSavedVersions()

    message.value =
      `AI 规划完成，已保存为版本 v${result.version}`
  } catch (err) {
    error.value = err.message || 'AI 规划失败'
  } finally {
    generating.value = false
  }
}

function resetForm() {
  tripId.value = null
  generated.value = null
  error.value = ''
  message.value = ''
}

function formatTime(value) {
  return String(value || '').slice(0, 5)
}
</script>

<template>
  <div class="planning-page">
    <div class="planning-intro">
      <div>
        <span class="planning-eyebrow">AI TRAVEL PLANNER</span>
        <h2>定制你的专属旅行</h2>
        <p>告诉 AI 你的旅行偏好，我们帮你设计每日路线。</p>
      </div>
      <span class="planning-mode"> LangGraph Agent</span>
    </div>

        <section class="existing-trip-selector">
      <div>
        <strong>继续规划已有旅行</strong>
        <p>选择之前创建的项目，自动加载已保存的旅行需求。</p>
      </div>
      <select
        v-model="selectedExistingId"
        :disabled="loading || generating || selectingTrip"
        @change="loadExistingTrip"
      >
        <option value="">选择已有旅行项目</option>
        <option
          v-for="trip in existingTrips"
          :key="trip.id"
          :value="String(trip.id)"
        >
          #{{ trip.id }}  {{ trip.title }}  {{ trip.destination }}
        </option>
      </select>
    </section>
    <div class="planning-layout">
      <section class="planning-form-card">
        <div class="planning-section-heading">
          <span class="planning-number">01</span>
          <div>
            <h3>基础旅行信息</h3>
            <p>填写目的地、日期及出行人数</p>
          </div>
        </div>

        <div class="planning-fields">
          <label class="planning-field full">
            <span>旅行名称 *</span>
            <input v-model="form.title" :disabled="tripId !== null"
              placeholder="例如：杭州三日游" />
          </label>

          <label class="planning-field">
            <span>旅行目的地 *</span>
            <input v-model="form.destination" :disabled="tripId !== null"
              placeholder="例如：杭州" />
          </label>

          <label class="planning-field">
            <span>出发城市 *</span>
            <input v-model="form.departure_city"
              placeholder="例如：南京" />
          </label>

          <label class="planning-field">
            <span>开始日期 *</span>
            <input v-model="form.start_date" type="date" />
          </label>

          <label class="planning-field">
            <span>结束日期 *</span>
            <input v-model="form.end_date" type="date" />
          </label>

          <label class="planning-field">
            <span>出行人数</span>
            <input v-model.number="form.travelers"
              type="number" min="1" max="50" />
          </label>

          <label class="planning-field">
            <span>交通偏好</span>
            <select v-model="form.transport_preference">
              <option value="public_transport">公共交通</option>
              <option value="driving">自驾</option>
              <option value="walking">步行</option>
            </select>
          </label>
        </div>

        <div class="planning-section-heading second">
          <span class="planning-number">02</span>
          <div>
            <h3>旅行偏好</h3>
            <p>让 AI 更准确地理解你的需求</p>
          </div>
        </div>

        <div class="planning-fields">
          <label class="planning-field">
            <span>旅行风格</span>
            <select v-model="form.travel_style">
              <option value="sightseeing">观光游览</option>
              <option value="cultural">文化探索</option>
              <option value="nature">自然风光</option>
              <option value="food">美食探索</option>
              <option value="leisure">休闲度假</option>
            </select>
          </label>

          <label class="planning-field">
            <span>旅行节奏</span>
            <select v-model="form.travel_pace">
              <option value="relaxed">轻松</option>
              <option value="moderate">适中</option>
              <option value="intensive">紧凑</option>
            </select>
          </label>

          <label class="planning-field">
            <span>每日开始时间</span>
            <input v-model="form.daily_start_time" type="time" />
          </label>

          <label class="planning-field">
            <span>每日结束时间</span>
            <input v-model="form.daily_end_time" type="time" />
          </label>

          <label class="planning-field full">
            <span>住宿偏好</span>
            <input v-model="form.accommodation_preference"
              placeholder="例如：经济型酒店" />
          </label>

          <label class="planning-field full">
            <span>必去景点</span>
            <textarea v-model="form.must_visit_places" rows="2"
              placeholder="多个景点用逗号分隔" />
          </label>

          <label class="planning-field full">
            <span>不想去的景点</span>
            <textarea v-model="form.excluded_places" rows="2"
              placeholder="可留空" />
          </label>

          <label class="planning-field full">
            <span>喜欢的活动</span>
            <input v-model="form.preferred_activities"
              placeholder="例如：美食、城市观光" />
          </label>

          <label class="planning-field full">
            <span>其他特殊要求</span>
            <textarea v-model="form.special_requirements" rows="3"
              placeholder="例如：尽量减少步行，安排午休" />
          </label>
        </div>

        <div v-if="error" class="planning-error">{{ error }}</div>
        <div v-if="message" class="planning-success">{{ message }}</div>

        <div class="planning-actions">
          <button class="planning-save" :disabled="loading || generating"
            @click="saveRequirements">
            {{ loading ? '正在保存...' : ' 保存旅行需求' }}
          </button>

          <button class="planning-generate"
            :disabled="!canGenerate"
            @click="generatePlan">
            {{ generating ? 'AI 正在规划，请勿重复点击...' : '  开始 AI 规划' }}
          </button>
        </div>

        <div v-if="tripId !== null" class="planning-project-info">
          当前项目 ID：{{ tripId }}
          <button :disabled="loading || generating" @click="resetForm">
            创建另一个旅行
          </button>
        </div>
      </section>

      <aside class="planning-result-card">
        <div class="planning-result-heading">
          <span class="planning-result-icon"></span>
          <h3>AI 规划结果</h3>
          <p>生成成功后，在这里查看每日行程</p>
        </div>

        <div v-if="savedVersions.length" class="saved-version-switcher">
          <strong>历史行程版本</strong>
          <div>
            <button
              v-for="item in savedVersions"
              :key="item.version"
              :class="{ active: selectedVersion === item.version }"
              :disabled="historyLoading || generating"
              @click="loadSavedVersion(item.version)"
            >
              v{{ item.version }}
            </button>
          </div>
        </div>

        <div v-if="!generated" class="planning-empty">
          <div class="planning-empty-icon"></div>
          <strong>等待生成旅行计划</strong>
          <p>请先保存旅行需求，再启动 AI Agent。</p>
          <p>生成过程会调用大模型和高德地图。</p>
        </div>

        <template v-else>
          <div class="planning-result-stats">
            <div>
              <span>保存版本</span>
              <strong>v{{ generated.version }}</strong>
            </div>
            <div>
              <span>质量评分</span>
              <strong>{{ generated.quality_score ?? '' }}</strong>
            </div>
            <div>
              <span>规划天数</span>
              <strong>{{ generated.itinerary?.length || 0 }}</strong>
            </div>
          </div>

          <p class="planning-result-status">
            规划状态：{{ generated.status }}
          </p>

          <div v-for="day in generated.itinerary || []"
            :key="day.day" class="planning-result-day">
            <h4>第 {{ day.day }} 天  {{ day.date }}</h4>
            <p>{{ day.theme }}</p>
            <div v-for="(item, index) in day.activities || []"
              :key="index" class="planning-result-item">
              <span>
                {{ formatTime(item.start_time) }}
                
                {{ formatTime(item.end_time) }}
              </span>
              <strong>{{ item.place_name }}</strong>
            </div>
          </div>

          <div v-if="generated.route_warnings?.length"
            class="planning-error">
            <strong>交通提示</strong>
            <p v-for="(warning, index) in generated.route_warnings"
              :key="index">{{ warning }}</p>
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.planning-page { display: grid; gap: 22px; }
.planning-intro {
  display: flex; justify-content: space-between;
  align-items: center; gap: 20px;
}
.planning-eyebrow {
  color: #4683f4; font-size: 11px;
  font-weight: 800; letter-spacing: 1.5px;
}
.planning-intro h2 {
  font-size: 25px; margin: 9px 0;
  color: #1b3050;
}
.planning-intro p, .planning-section-heading p {
  color: #97a5b9; font-size: 12px; margin: 0;
}
.planning-mode {
  background: #edf4ff; color: #397bea;
  padding: 11px 15px; border-radius: 10px;
  font-size: 12px; font-weight: 700;
}
.planning-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, .85fr);
  gap: 20px; align-items: start;
}
.planning-form-card, .planning-result-card {
  background: white; border: 1px solid #e7edf7;
  border-radius: 16px; padding: 26px;
}
.planning-section-heading {
  display: flex; align-items: center;
  gap: 13px; margin-bottom: 20px;
}
.planning-section-heading.second {
  margin-top: 33px; padding-top: 26px;
  border-top: 1px solid #eef2f8;
}
.planning-section-heading h3 {
  font-size: 16px; margin: 0 0 5px;
}
.planning-number {
  display: grid; place-items: center;
  width: 40px; height: 40px;
  border-radius: 11px; background: #ecf4ff;
  color: #377cf2; font-weight: 800;
}
.planning-fields {
  display: grid; grid-template-columns: repeat(2,minmax(0,1fr));
  gap: 17px;
}
.planning-field {
  display: flex; flex-direction: column;
  gap: 9px; min-width: 0;
}
.planning-field.full { grid-column: 1 / -1; }
.planning-field span {
  font-size: 12px; font-weight: 700; color: #50647f;
}
.planning-field input,
.planning-field select,
.planning-field textarea {
  width: 100%; min-width: 0; padding: 12px 13px;
  border: 1px solid #dfe7f2; border-radius: 9px;
  outline: none; color: #243b5a; font: inherit;
  font-size: 13px; background: #fbfcff;
}
.planning-field input:focus,
.planning-field select:focus,
.planning-field textarea:focus {
  border-color: #4487f8;
  box-shadow: 0 0 0 3px #4487f817;
}
.planning-field textarea { resize: vertical; }
.planning-actions {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 12px; margin-top: 25px;
}
.planning-actions button {
  border: 0; border-radius: 9px; padding: 14px 10px;
  font-size: 12px; font-weight: 700; cursor: pointer;
}
.planning-save { background: #eaf2ff; color: #3278ea; }
.planning-generate { background: #377df2; color: white; }
.planning-actions button:disabled {
  opacity: .5; cursor: not-allowed;
}
.planning-error, .planning-success {
  margin-top: 16px; padding: 13px;
  border-radius: 9px; font-size: 12px; line-height: 1.7;
}
.planning-error { background: #fff0ed; color: #c3513d; }
.planning-success { background: #eaf9f1; color: #23976d; }
.planning-project-info {
  display: flex; justify-content: space-between;
  align-items: center; margin-top: 16px;
  color: #8295ae; font-size: 12px;
}
.planning-project-info button {
  border: 0; background: transparent;
  color: #3c7eee; font-weight: 700; cursor: pointer;
}
.planning-result-card { position: sticky; top: 92px; }
.planning-result-heading { text-align: center; padding: 12px 0 25px; }
.planning-result-heading h3 { margin: 12px 0 7px; font-size: 18px; }
.planning-result-heading p {
  color: #99a8bb; font-size: 12px; margin: 0;
}
.planning-result-icon {
  background: #eaf2ff; color: #3e7ff2;
  display: inline-grid; place-items: center;
  width: 48px; height: 48px; border-radius: 13px;
  font-size: 25px;
}
.planning-empty {
  background: #f7faff; border-radius: 13px;
  padding: 60px 18px; text-align: center;
}
.planning-empty-icon { font-size: 39px; color: #7fa4e9; }
.planning-empty strong { font-size: 14px; color: #405b80; }
.planning-empty p { color: #9aa9bd; font-size: 12px; line-height: 1.7; }
.planning-result-stats {
  display: grid; grid-template-columns: repeat(3,1fr);
  gap: 9px;
}
.planning-result-stats div {
  padding: 14px; background: #f4f8fe; border-radius: 10px;
}
.planning-result-stats span {
  display: block; color: #91a0b4; font-size: 11px;
}
.planning-result-stats strong {
  display: block; margin-top: 7px; font-size: 22px;
  color: #23436d;
}
.planning-result-status {
  font-size: 12px; color: #5578b2; margin: 20px 0;
}
.planning-result-day {
  padding: 18px 0; border-top: 1px solid #edf1f8;
}
.planning-result-day h4 { font-size: 13px; margin: 0 0 7px; }
.planning-result-day > p {
  font-size: 12px; color: #91a1b7; margin: 0 0 12px;
}
.planning-result-item { padding: 10px 0; display: grid; gap: 6px; }
.planning-result-item span { color: #4b81e6; font-size: 11px; }
.planning-result-item strong { font-size: 12px; }
@media (max-width: 1050px) {
  .planning-layout { grid-template-columns: 1fr; }
  .planning-result-card { position: static; }
}
@media (max-width: 600px) {
  .planning-fields, .planning-actions { grid-template-columns: 1fr; }
  .planning-form-card, .planning-result-card { padding: 16px; }
  .planning-intro { display: block; }
  .planning-mode { display: inline-block; margin-top: 14px; }
}
.existing-trip-selector {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 22px 25px;
  background: #fff;
  border: 1px solid #e7edf7;
  border-radius: 14px;
}
.existing-trip-selector strong {
  font-size: 15px;
  color: #213a60;
}
.existing-trip-selector p {
  color: #94a4ba;
  font-size: 12px;
  margin: 7px 0 0;
}
.existing-trip-selector select {
  min-width: 260px;
  max-width: 100%;
  border: 1px solid #dce6f5;
  background: #f8fbff;
  border-radius: 9px;
  padding: 12px;
  color: #355d9c;
  font-size: 12px;
}
@media (max-width: 750px) {
  .existing-trip-selector {
    display: block;
  }
  .existing-trip-selector select {
    width: 100%;
    margin-top: 15px;
  }
}
.saved-version-switcher {
  padding: 16px 0;
  margin-bottom: 18px;
  border-top: 1px solid #edf1f8;
  border-bottom: 1px solid #edf1f8;
}
.saved-version-switcher strong {
  display: block;
  color: #344b6c;
  font-size: 12px;
  margin-bottom: 12px;
}
.saved-version-switcher > div {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}
.saved-version-switcher button {
  border: 1px solid #dce6f6;
  background: white;
  color: #5780c5;
  border-radius: 8px;
  padding: 9px 15px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.saved-version-switcher button.active {
  background: #3e7df0;
  color: white;
  border-color: #3e7df0;
}
.saved-version-switcher button:disabled {
  opacity: .5;
  cursor: not-allowed;
}
</style>
