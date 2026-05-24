/**
 * 嵌套组件文件 - 深度 7
 */

import { NestedComponent8 } from './NestedComponent8';

@Component
export struct NestedComponent7 {
    build() {
        Column() {
            NestedComponent8()
            NestedComponent8()
        }
    }
}
