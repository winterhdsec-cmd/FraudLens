import { inject, ref } from 'vue'

// 全局数据缓存
const dataCache = new Map()
const loadingPromises = new Map()

// 缓存有效期（毫秒）
const CACHE_TTL = 30000 // 30秒

// 通用数据加载器（带缓存）
export function useCachedLoader() {
  const cachedLoad = async (key, loader, ttl = CACHE_TTL) => {
    const now = Date.now()
    const cached = dataCache.get(key)
    
    // 检查缓存是否存在且未过期
    if (cached && (now - cached.timestamp < ttl)) {
      return cached.data
    }
    
    // 如果正在加载中，返回同一个 Promise
    if (loadingPromises.has(key)) {
      return loadingPromises.get(key)
    }
    
    // 开始加载
    const promise = loader().then(data => {
      dataCache.set(key, { data, timestamp: Date.now() })
      loadingPromises.delete(key)
      return data
    }).catch(err => {
      loadingPromises.delete(key)
      throw err
    })
    
    loadingPromises.set(key, promise)
    return promise
  }
  
  const invalidateCache = (key) => {
    dataCache.delete(key)
  }
  
  const clearAllCache = () => {
    dataCache.clear()
  }
  
  return { cachedLoad, invalidateCache, clearAllCache }
}

export function useAppState() {
  return inject('appState')
}