/**
 * 嵌套组件文件 - 深度 17
 */

import { NestedComponent18 } from './NestedComponent18';

@Component
export struct NestedComponent17 {
    build() {
        Column() {
            NestedComponent18()
            NestedComponent18()
        }
    }
}
