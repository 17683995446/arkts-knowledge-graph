/**
 * 嵌套组件文件 - 深度 16
 */

import { NestedComponent17 } from './NestedComponent17';

@Component
export struct NestedComponent16 {
    build() {
        Column() {
            NestedComponent17()
            NestedComponent17()
        }
    }
}
