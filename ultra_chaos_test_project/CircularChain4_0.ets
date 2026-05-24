/**
 * 循环导入链 4, 文件 0
 */

import { Class1 } from './CircularChain4_1';

export class Class0 {
    use1() {
        return new Class1();
    }
}
