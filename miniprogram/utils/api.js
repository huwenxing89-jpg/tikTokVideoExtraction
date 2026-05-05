// utils/api.js
// API 接口封装

const app = getApp()

/**
 * 解析抖音分享链接
 * @param {string} shareText - 分享文本
 * @returns {Promise} 解析结果
 */
function parseVideo(shareText) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.baseUrl}/api/parse`,
      method: 'POST',
      data: {
        url: shareText
      },
      header: {
        'content-type': 'application/json'
      },
      timeout: 30000, // 30秒超时
      success(res) {
        if (res.data.success) {
          resolve(res.data.data)
        } else {
          reject(new Error(res.data.message || '解析失败'))
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || '网络请求失败'))
      }
    })
  })
}

/**
 * 检测视频清晰度
 * @param {Array} urls - URL列表
 * @returns {Promise} 检测结果
 */
function checkQuality(urls) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.baseUrl}/api/check_quality`,
      method: 'POST',
      data: { urls },
      header: {
        'content-type': 'application/json'
      },
      success(res) {
        if (res.data.success) {
          resolve(res.data.results)
        } else {
          reject(new Error(res.data.message || '检测失败'))
        }
      },
      fail(err) {
        reject(new Error('网络请求失败'))
      }
    })
  })
}

/**
 * 获取代理视频URL
 * @param {string} videoUrl - 原始视频URL
 * @returns {string} 代理URL
 */
function getProxyVideoUrl(videoUrl) {
  return `${app.globalData.baseUrl}/api/proxy/video?url=${encodeURIComponent(videoUrl)}`
}

/**
 * 获取代理图片URL（用于加载抖音图片，绕过防盗链）
 * @param {string} imageUrl - 原始图片URL
 * @returns {string} 代理URL
 */
function getProxyImageUrl(imageUrl) {
  return `${app.globalData.baseUrl}/api/proxy/image?url=${encodeURIComponent(imageUrl)}`
}

/**
 * 获取下载URL
 * @param {string} videoUrl - 原始视频URL
 * @param {string} filename - 文件名
 * @returns {string} 下载URL
 */
function getDownloadUrl(videoUrl, filename) {
  return `${app.globalData.baseUrl}/api/proxy/video?url=${encodeURIComponent(videoUrl)}&download=1&filename=${encodeURIComponent(filename)}`
}

/**
 * 格式化数字（如：1.2万）
 * @param {number} num - 数字
 * @returns {string} 格式化后的字符串
 */
function formatNumber(num) {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

/**
 * 格式化时长
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的时长
 */
function formatDuration(seconds) {
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}

module.exports = {
  parseVideo,
  checkQuality,
  getProxyVideoUrl,
  getProxyImageUrl,
  getDownloadUrl,
  formatNumber,
  formatDuration
}
