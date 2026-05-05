// pages/result/result.js
const api = require('../../utils/api')

Page({
  data: {
    videoInfo: null,
    proxyVideoUrl: '',
    currentImageIndex: 0,
    downloading: false
  },

  onLoad(options) {
    if (options.data) {
      try {
        const videoInfo = JSON.parse(decodeURIComponent(options.data))
        const proxyVideoUrl = videoInfo.video_url ? api.getProxyVideoUrl(videoInfo.video_url) : ''

        // 代理图片URL（绕过防盗链）
        const proxyAuthorAvatar = videoInfo.author_avatar ? api.getProxyImageUrl(videoInfo.author_avatar) : ''
        const proxyCoverUrl = videoInfo.cover_url ? api.getProxyImageUrl(videoInfo.cover_url) : ''
        const proxyImages = videoInfo.images ? videoInfo.images.map(img => api.getProxyImageUrl(img)) : []

        // 预格式化数据
        const formattedData = {
          ...videoInfo,
          durationText: this.formatDuration(videoInfo.duration || 0),
          likeText: this.formatCount(videoInfo.like_count || 0),
          commentText: this.formatCount(videoInfo.comment_count || 0),
          shareText: this.formatCount(videoInfo.share_count || 0),
          // 使用代理后的URL
          author_avatar: proxyAuthorAvatar,
          cover_url: proxyCoverUrl,
          images: proxyImages
        }

        this.setData({
          videoInfo: formattedData,
          proxyVideoUrl
        })
      } catch (e) {
        wx.showToast({ title: '数据解析失败', icon: 'none' })
        setTimeout(() => wx.navigateBack(), 1500)
      }
    }
  },

  // 格式化时长
  formatDuration(seconds) {
    const min = Math.floor(seconds / 60)
    const sec = seconds % 60
    return `${min}:${sec.toString().padStart(2, '0')}`
  },

  // 格式化数量
  formatCount(num) {
    if (num >= 10000) {
      return (num / 10000).toFixed(1) + '万'
    }
    return num.toString()
  },

  // 图片切换
  onImageChange(e) {
    this.setData({
      currentImageIndex: e.detail.current
    })
  },

  // 预览图片（使用原始URL预览，预览接口不受防盗链限制）
  previewImage(e) {
    const { src } = e.currentTarget.dataset
    // 预览使用代理后的URL
    const images = this.data.videoInfo.images

    wx.previewImage({
      current: src,
      urls: images
    })
  },

  // 保存全部图片
  async saveAllImages() {
    const images = this.data.videoInfo.images
    if (!images || images.length === 0) return

    this.setData({ downloading: true })

    let successCount = 0
    let failCount = 0

    for (const imgUrl of images) {
      try {
        const downloadRes = await wx.downloadFile({ url: imgUrl })
        if (downloadRes.statusCode === 200) {
          await wx.saveImageToPhotosAlbum({
            filePath: downloadRes.tempFilePath
          })
          successCount++
        } else {
          failCount++
        }
      } catch (e) {
        failCount++
      }
    }

    this.setData({ downloading: false })

    if (failCount === 0) {
      wx.showToast({ title: `已保存${successCount}张图片`, icon: 'success' })
    } else {
      wx.showToast({
        title: `成功${successCount}张，失败${failCount}张`,
        icon: 'none'
      })
    }
  },

  // 复制视频链接
  copyVideoUrl() {
    const { videoInfo } = this.data
    if (!videoInfo || !videoInfo.video_url) return

    wx.setClipboardData({
      data: videoInfo.video_url,
      success: () => {
        wx.showToast({ title: '链接已复制', icon: 'success' })
      }
    })
  },

  // 直接下载视频到相册
  async downloadVideo() {
    const { videoInfo } = this.data
    if (!videoInfo || !videoInfo.video_url) {
      wx.showToast({ title: '视频地址无效', icon: 'none' })
      return
    }

    this.setData({ downloading: true })
    wx.showLoading({ title: '下载中...', mask: true })

    try {
      // 构建下载URL（通过服务器代理）
      const app = getApp()
      const downloadUrl = `${app.globalData.baseUrl}/api/proxy/video?url=${encodeURIComponent(videoInfo.video_url)}&download=1`

      console.log('下载URL:', downloadUrl)

      // 下载视频文件
      const downloadRes = await new Promise((resolve, reject) => {
        wx.downloadFile({
          url: downloadUrl,
          timeout: 120000,
          success: resolve,
          fail: reject
        })
      })

      console.log('下载结果:', downloadRes.statusCode, downloadRes.tempFilePath)

      if (downloadRes.statusCode === 200) {
        // 保存视频到相册
        await wx.saveVideoToPhotosAlbum({
          filePath: downloadRes.tempFilePath
        })

        wx.showToast({ title: '已保存到相册', icon: 'success' })
      } else {
        throw new Error(`下载失败: HTTP ${downloadRes.statusCode}`)
      }
    } catch (e) {
      console.error('下载视频失败:', e)

      if (e.errMsg && e.errMsg.includes('auth deny')) {
        wx.showModal({
          title: '提示',
          content: '需要您授权保存视频到相册',
          confirmText: '去授权',
          success: (res) => {
            if (res.confirm) {
              wx.openSetting()
            }
          }
        })
      } else {
        wx.showModal({
          title: '下载失败',
          content: e.errMsg || e.message || '请尝试复制链接在浏览器下载',
          showCancel: false
        })
      }
    } finally {
      wx.hideLoading()
      this.setData({ downloading: false })
    }
  },

  // 打开视频链接
  openVideoUrl() {
    const { videoInfo } = this.data
    if (!videoInfo || !videoInfo.video_url) return

    // 复制链接，提示用户在浏览器打开
    wx.setClipboardData({
      data: videoInfo.video_url,
      success: () => {
        wx.showModal({
          title: '提示',
          content: '视频链接已复制，请在浏览器中打开下载',
          showCancel: false
        })
      }
    })
  },

  // 分享
  onShareAppMessage() {
    const { videoInfo } = this.data
    return {
      title: videoInfo?.title || '抖音视频下载',
      path: '/pages/index/index'
    }
  },

  // 返回首页
  goBack() {
    wx.navigateBack()
  }
})
