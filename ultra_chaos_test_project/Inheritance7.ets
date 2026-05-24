/**
 * 继承层次结构 - 中间层 7
 */

import { BaseClass6 } from './Inheritance6';

export abstract class BaseClass7 extends BaseClass6 {
    intermediateMethod(): void {
        console.log('intermediate method 7');
    }
}
