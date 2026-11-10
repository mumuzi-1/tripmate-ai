<script setup>
import { ref } from 'vue'
import { login } from '../api/client'

const emit = defineEmits(['success'])

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')
const showPassword = ref(false)

async function handleLogin() {
  errorMessage.value = ''

  if (!username.value.trim() || !password.value) {
    errorMessage.value = '请输入用户名和密码'
    return
  }

  loading.value = true

  try {
    await login(username.value.trim(), password.value)
    emit('success')
  } catch (error) {
    errorMessage.value = error.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-intro">
      <div class="login-brand">
        <div class="login-brand-icon"></div>
        <div>
          <strong>TripMate AI</strong>
          <small>智能旅行规划平台</small>
        </div>
      </div>

      <div class="login-intro-main">
        <span class="login-eyebrow">YOUR AI TRAVEL COMPANION</span>
        <h1>
          每一段旅程，<br />
          都值得<span>精心规划。</span>
        </h1>
        <p>
          智能推荐旅行景点、自动安排游玩路线，<br />
          让 AI 帮你把旅行灵感变成精彩行程。
        </p>

        <div class="login-features">
          <div><span></span> AI 智能规划</div>
          <div><span></span> 地图路线优化</div>
          <div><span></span> 行程质量校验</div>
        </div>
      </div>

      <div class="login-intro-footer">
        TRIPMATE AI  EXPLORE MORE, PLAN LESS
      </div>
    </div>

    <div class="login-form-side">
      <div class="login-panel">
        <div class="login-icon"></div>

        <div class="login-welcome">
          <span>WELCOME BACK</span>
          <h2>欢迎回来</h2>
          <p>登录账号，继续探索你的下一段旅程。</p>
        </div>

        <form @submit.prevent="handleLogin">
          <div class="login-field">
            <label for="tripmate-username">用户名或邮箱</label>
            <input
              id="tripmate-username"
              v-model="username"
              type="text"
              autocomplete="username"
              placeholder="请输入用户名或邮箱"
              :disabled="loading"
            />
          </div>

          <div class="login-field">
            <label for="tripmate-password">登录密码</label>

            <div class="password-wrap">
              <input
                id="tripmate-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入登录密码"
                :disabled="loading"
              />
              <button
                type="button"
                class="password-toggle"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </div>
          </div>

          <p v-if="errorMessage" class="login-error" role="alert">
            {{ errorMessage }}
          </p>

          <button
            type="submit"
            class="login-submit"
            :disabled="loading"
          >
            {{ loading ? '正在登录...' : '登录 TripMate AI' }}
            <span v-if="!loading"></span>
          </button>
        </form>

        <div class="login-note">
          当前为本地开发环境，请使用已注册的 TripMate 账号登录。
        </div>
      </div>
    </div>
  </div>
</template>
