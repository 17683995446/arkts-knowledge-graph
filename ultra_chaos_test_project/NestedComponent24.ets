/**
 * 嵌套组件文件 - 深度 24
 */

import { NestedComponent25 } from './NestedComponent25';

@Component
export struct NestedComponent24 {
    build() {
        Column() {
            NestedComponent25()
            NestedComponent25()
        }
    }
}
