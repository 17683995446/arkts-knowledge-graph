
// 日期工具类
export class DateUtils {
  static format(date: Date, pattern: string): string {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return pattern.replace('YYYY', String(year)).replace('MM', month).replace('DD', day)
  }
  
  static parse(dateStr: string): Date {
    return new Date(dateStr)
  }
  
  static addDays(date: Date, days: number): Date {
    const result = new Date(date)
    result.setDate(result.getDate() + days)
    return result
  }
  
  static isToday(date: Date): boolean {
    const today = new Date()
    return date.toDateString() === today.toDateString()
  }
}

// 字符串工具类
export class StringUtils {
  static isEmpty(s: string): boolean {
    return s === null || s === undefined || s.trim() === ''
  }
  
  static capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1)
  }
  
  static truncate(s: string, maxLength: number): string {
    return s.length > maxLength ? s.slice(0, maxLength) + '...' : s
  }
  
  static mask(s: string, start: number, end: number, maskChar: string = '*'): string {
    if (s.length <= start + end) return s
    return s.slice(0, start) + maskChar.repeat(s.length - start - end) + s.slice(-end)
  }
}

// 数字工具类
export class NumberUtils {
  static format(n: number, decimals: number = 2): string {
    return n.toFixed(decimals)
  }
  
  static clamp(n: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, n))
  }
  
  static random(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min
  }
  
  static isInteger(n: number): boolean {
    return Number.isInteger(n)
  }
}

// 验证工具类
export class ValidationUtils {
  static isEmail(email: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  }
  
  static isPhone(phone: string): boolean {
    return /^\d{11}$/.test(phone)
  }
  
  static isUrl(url: string): boolean {
    return /^https?:\/\/.+/.test(url)
  }
  
  static isIdCard(idCard: string): boolean {
    return /^\d{17}[\dXx]$/.test(idCard)
  }
}
