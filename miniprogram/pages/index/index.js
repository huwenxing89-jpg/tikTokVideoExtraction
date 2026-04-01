// pages/index/index.js
const api = require('../../utils/api')

Page({
  data: {
    shareText: '',
    loading: false,
    history: []
  },

  onLoad() {
    // 加载历史记录
    const history = wx.getStorageSync('parseHistory') || []
    this.setData({ history: history.slice(0, 10) }) // 最多显示10条
  },

  // 输入框内容变化
  onInput(e) {
    this.setData({
      shareText: e.detail.value
    })
  },

  // 清空输入
  clearInput() {
    this.setData({ shareText: '' })
  },

  // 粘贴剪贴板内容
  async pasteFromClipboard() {
    try {
      const res = await wx.getClipboardData()
      if (res.data) {
        this.setData({ shareText: res.data })
        wx.showToast({ title: '已粘贴', icon: 'success' })
      }
    } catch (e) {
      wx.showToast({ title: '粘贴失败', icon: 'none' })
    }
  },

  // 解析视频
  async parseVideo() {
    const { shareText } = this.data

    if (!shareText.trim()) {
      wx.showToast({ title: '请输入分享链接', icon: 'none' })
      return
    }

    // 检查是否包含抖音链接
    if (!shareText.includes('douyin.com')) {
      wx.showToast({ title: '请输入有效的抖音链接', icon: 'none' })
      return
    }

    this.setData({ loading: true })

    try {
      const result = await api.parseVideo(shareText)

      // 保存到历史记录
      this.saveHistory(result)

      // 跳转到结果页
      wx.navigateTo({
        url: `/pages/result/result?data=${encodeURIComponent(JSON.stringify(result))}`
      })
    } catch (e) {
      wx.showToast({ title: e.message || '解析失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // 保存历史记录
  saveHistory(result) {
    let history = wx.getStorageSync('parseHistory') || []

    // 添加新记录到开头
    history.unshift({
      title: result.title || '无标题',
      author: result.author,
      cover: result.cover_url,
      type: result.content_type,
      time: Date.now()
    })

    // 最多保存20条
    history = history.slice(0, 20)
    wx.setStorageSync('parseHistory', history)
    this.setData({ history: history.slice(0, 10) })
  },

  // 点击历史记录
  onHistoryTap(e) {
    const { index } = e.currentTarget.dataset
    const item = this.data.history[index]
    // 历史记录只显示，不重新解析（需要重新输入链接）
    wx.showToast({ title: '请重新输入链接', icon: 'none' })
  },

  // 清空历史
  clearHistory() {
    wx.showModal({
      title: '提示',
      content: '确定清空历史记录？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('parseHistory')
          this.setData({ history: [] })
          wx.showToast({ title: '已清空', icon: 'success' })
        }
      }
    })
  },

  // 使用说明
  showHelp() {
    wx.showModal({
      title: '使用说明',
      content: '1. 打开抖音APP，找到想下载的视频\n2. 点击右侧"分享"按钮\n3. 选择"复制链接"\n4. 返回小程序，粘贴链接\n5. 点击"解析视频"按钮\n\n支持视频和图文作品',
      showCancel: false,
      confirmText: '知道了'
    })
  }
})
